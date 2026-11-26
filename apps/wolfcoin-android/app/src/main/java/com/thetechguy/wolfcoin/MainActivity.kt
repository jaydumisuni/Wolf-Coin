package com.thetechguy.wolfcoin

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.pm.PackageManager
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.os.Message
import android.util.Base64
import android.view.View
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import androidx.webkit.JavaScriptReplyProxy
import androidx.webkit.ProfileStore
import androidx.webkit.WebMessageCompat
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener
import java.io.ByteArrayOutputStream
import java.net.URI
import java.security.MessageDigest
import java.time.Instant
import java.util.Collections
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import com.chaquo.python.Python
import com.chaquo.python.PyObject
import com.chaquo.python.android.AndroidPlatform

/**
 * Wolf-Coin v0.9 native Android browser and signed application backend. UI and credentials never share a WebView.
 * All browser observations are candidates, not verified broker/bookmaker balances.
 */
class MainActivity : Activity() {
    companion object {
        const val ORIGIN = "https://appassets.androidplatform.net"
        const val CONTRACT = "wolf.browser.v1"
        const val UI_URL = "$ORIGIN/assets/wolfcoin.html"
        const val WEBSITE_PERMISSION_REQUEST = 8107
    }
    private lateinit var root: FrameLayout
    private lateinit var ui: WebView
    private val sessions = HashMap<String, WebView>()
    private val popupOwners = LinkedHashMap<WebView,String>()
    private val requested = HashMap<String, String>()
    private val network = ConcurrentHashMap<String, MutableList<JSONObject>>()
    private var activeId: String? = null
    private var pendingWebPermission: PermissionRequest? = null
    private val backendWorker=Executors.newSingleThreadExecutor()
    private var nativePythonBackend:PyObject?=null
    private val passwords by lazy { PasswordStore(this) }

    private fun signedBackend():PyObject {
        val current=nativePythonBackend
        if(current!=null)return current
        val created=Python.getInstance().getModule("wolf_native_api")
            .callAttr("WolfNativeApp",filesDir.absolutePath)
        nativePythonBackend=created
        return created
    }
    private fun backendCall(id:String,operation:String,payload:JSONObject,
                            reply:JavaScriptReplyProxy,isStatus:Boolean=false){
        backendWorker.execute{
            try{
                val result=JSONObject(signedBackend().callAttr("request",operation,payload.toString()).toString())
                val data=result.optJSONObject("data")?:JSONObject()
                runOnUiThread{
                    if(result.optString("status")=="OK"){
                        if(isStatus)respond(reply,id,JSONObject()
                            .put("available",true).put("schema","wolf.app.bridge.v2")
                            .put("host","android-embedded-python"))
                        else respond(reply,id,data)
                    }else respond(reply,id,null,data.optString("error","Native backend rejected request"))
                }
            }catch(e:Exception){
                runOnUiThread{respond(reply,id,null,"Native backend: "+(e.message?:"runtime failure"))}
            }
        }
    }

    private var area = intArrayOf(0, 0, 0, 0)
    private val snapshotScript by lazy { assets.open("wolf_snapshot.js").bufferedReader().use { it.readText() } }
    private val assetLoader by lazy {
        WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if(!Python.isStarted())Python.start(AndroidPlatform(this))
        if ((applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
            WebView.setWebContentsDebuggingEnabled(true) // local emulator/ADB proof only
        }
        window.statusBarColor = Color.rgb(5, 12, 24)
        window.navigationBarColor = Color.rgb(5, 12, 24)
        root = FrameLayout(this)
        ui = WebView(this)
        ui.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            cacheMode = WebSettings.LOAD_DEFAULT
        }
        ui.webChromeClient = WebChromeClient()
        ui.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest?): WebResourceResponse? {
                return request?.url?.let { assetLoader.shouldInterceptRequest(it) }
            }
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val link = request?.url ?: return true
                if (link.toString().startsWith(ORIGIN + "/assets/")) return false
                return true // untrusted sites never replace the privileged frontend
            }
        }
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            // Refuse an insecure fallback that would expose a JavaScript interface to external sites.
            root.addView(ui, FrameLayout.LayoutParams(-1, -1))
            setContentView(root)
            ui.loadDataWithBaseURL(ORIGIN,
                "<h3 style='color:white;background:#080f1f;padding:24px'>Wolf-Coin needs an updated Android System WebView supporting isolated messaging.</h3>",
                "text/html", "utf-8", null)
            return
        }
        WebViewCompat.addWebMessageListener(ui, "WolfHost", setOf(ORIGIN),
            WebViewCompat.WebMessageListener { view: WebView, msg: WebMessageCompat,
                                                  source: Uri, mainFrame: Boolean, reply: JavaScriptReplyProxy ->
                if (view !== ui || !mainFrame || source.toString() != ORIGIN) return@WebMessageListener
                val request = try { JSONObject(msg.data ?: "") } catch (_: Exception) { return@WebMessageListener }
                val id = request.optString("id").take(64)
                if (id.isEmpty()) return@WebMessageListener
                try {
                    dispatch(id, request.getString("method"), request.optJSONObject("args") ?: JSONObject(), reply)
                } catch (e: Exception) { respond(reply, id, null, e.message ?: "Browser host error") }
            })
        root.addView(ui, FrameLayout.LayoutParams(-1, -1))
        setContentView(root)
        if (savedInstanceState == null) ui.loadUrl(UI_URL)
        else if (ui.restoreState(savedInstanceState) == null) ui.loadUrl(UI_URL)
    }

    private fun respond(reply: JavaScriptReplyProxy, id: String, result: Any?, error: String? = null) {
        val packet = JSONObject().put("id", id).put("ok", error == null)
        if (error == null) packet.put("result", result ?: JSONObject())
        else packet.put("error", error)
        reply.postMessage(packet.toString())
    }

    private fun accountId(id: String): String {
        require(id.matches(Regex("[A-Za-z0-9_:-]{1,128}"))) { "Invalid account ID" }
        return id
    }
    private fun profileName(id: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(accountId(id).toByteArray())
        return "wolf-" + digest.take(16).joinToString("") { "%02x".format(it) }
    }
    private fun safeUrl(value: String): String {
        val link = URI(value)
        require(link.userInfo == null && link.host != null) { "Invalid website URL" }
        require(link.scheme.equals("https", true) || link.scheme.equals("http", true)) {
            "Only HTTP(S) websites are supported"
        }
        return link.toString()
    }
    private fun activeBrowser(id: String): WebView {
        require(activeId == accountId(id)) { "Account/browser session mismatch" }
        return sessions[id] ?: error("No active browser")
    }
    private fun currentBrowser(id: String): WebView {
        sessions[id]?.let { return it }
        check(WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE)) {
            "This Android System WebView cannot isolate account profiles. Please update WebView."
        }
        val browser = WebView(this)
        // Must be set before any settings evaluation/navigation on this instance.
        WebViewCompat.setProfile(browser, profileName(id))
        browser.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            setSupportMultipleWindows(true)
            javaScriptCanOpenWindowsAutomatically = true
        }
        browser.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread {
                    val origin = request.origin?.toString() ?: "Website"
                    AlertDialog.Builder(this@MainActivity)
                        .setTitle("Website permission")
                        .setMessage(origin+" requests: "+request.resources.joinToString(", "))
                        .setPositiveButton("Allow") { _, _ ->
                            val androidPermissions = mutableListOf<String>()
                            if (request.resources.contains(PermissionRequest.RESOURCE_VIDEO_CAPTURE))
                                androidPermissions.add(Manifest.permission.CAMERA)
                            if (request.resources.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
                                androidPermissions.add(Manifest.permission.RECORD_AUDIO)
                            val needed = androidPermissions.filter {
                                checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED
                            }
                            if (needed.isEmpty()) request.grant(request.resources)
                            else {
                                pendingWebPermission=request
                                requestPermissions(needed.toTypedArray(),WEBSITE_PERMISSION_REQUEST)
                            }
                        }
                        .setNegativeButton("Deny") { _, _ -> request.deny() }
                        .setOnCancelListener { request.deny() }
                        .show()
                }
            }
            override fun onPermissionRequestCanceled(request: PermissionRequest) {
                if (pendingWebPermission === request) pendingWebPermission=null
            }
            override fun onCreateWindow(view: WebView?, isDialog:Boolean, isUserGesture:Boolean,
                                        resultMsg:Message?):Boolean {
                val transport=resultMsg?.obj as? WebView.WebViewTransport ?: return false
                val popup=WebView(this@MainActivity)
                WebViewCompat.setProfile(popup,profileName(id))
                popup.settings.apply {
                    javaScriptEnabled=true
                    domStorageEnabled=true
                    allowFileAccess=false
                    allowContentAccess=false
                    mixedContentMode=WebSettings.MIXED_CONTENT_NEVER_ALLOW
                    setSupportMultipleWindows(true)
                    javaScriptCanOpenWindowsAutomatically=true
                }
                popup.webChromeClient=this
                popup.webViewClient=object : WebViewClient() {
                    override fun shouldOverrideUrlLoading(view:WebView?,request:WebResourceRequest?):Boolean {
                        return try { safeUrl(request?.url?.toString() ?: "");false }
                        catch (_: Exception) { true }
                    }
                    override fun onPageFinished(view:WebView?,url:String?) {
                        try { view?.let { WebViewCompat.getProfile(it).cookieManager.flush() } }
                        catch (_:Exception) {}
                    }
                }
                popupOwners[popup]=id
                root.addView(popup,FrameLayout.LayoutParams(-1,-1))
                popup.bringToFront()
                transport.webView=popup
                resultMsg.sendToTarget()
                return true
            }
            override fun onCloseWindow(window:WebView?) {
                window?.let{closePopup(it)}
            }
        }
        browser.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                return try { safeUrl(request?.url?.toString() ?: ""); false } catch (_: Exception) { true }
            }
            override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest?): WebResourceResponse? {
                val req = request ?: return null
                try {
                    val link = URI(req.url.toString())
                    val safePath=link.path.split("/").joinToString("/") { segment ->
                        if (segment.length>28 || segment.matches(Regex("(?i)^[a-f0-9]{24,}$"))) ":opaque" else segment
                    }.take(160)
                    val entry=JSONObject().put("at",Instant.now().toString())
                        .put("method",req.method).put("url",link.scheme+"://"+link.authority+safePath)
                        .put("resourceType",if(req.isForMainFrame) "document" else "subresource")
                    val list=network.computeIfAbsent(id) { Collections.synchronizedList(mutableListOf()) }
                    synchronized(list) {list.add(entry);while(list.size>120)list.removeAt(0)}
                } catch (_: Exception) {}
                return null
            }
            override fun onPageFinished(view: WebView?, url: String?) {
                // Persist the account's named WebView cookie jar after authenticated redirects.
                try { view?.let { WebViewCompat.getProfile(it).cookieManager.flush() } }
                catch (e: Exception) { android.util.Log.w("WolfBrowser", "Cookie persistence: "+e.message) }
                if (activeId == id) sendPageState(id, url ?: "", view?.title ?: "")
                if(view!=null) fillSavedLogin(id,view,true,null,null)
            }
        }
        sessions[id] = browser
        return browser
    }
    private fun closePopup(popup:WebView){
        popupOwners.remove(popup)
        if(popup.parent==root)root.removeView(popup)
        popup.stopLoading()
        popup.destroy()
    }
    private fun sendPageState(id: String, url: String, title: String) {
        val data = JSONObject().put("schema", CONTRACT).put("accountId", id)
            .put("url", url).put("title", title).put("observedAt", Instant.now().toString())
        ui.evaluateJavascript("window.__wolfAndroidPageState && window.__wolfAndroidPageState(${data})", null)
    }
    private fun bounds(rect: JSONObject) {
        val scale = resources.displayMetrics.density
        val x = (rect.optDouble("x", 0.0) * scale).toInt().coerceAtLeast(0)
        val y = (rect.optDouble("y", 0.0) * scale).toInt().coerceAtLeast(0)
        val w = (rect.optDouble("width", 0.0) * scale).toInt().coerceAtLeast(0)
        val h = (rect.optDouble("height", 0.0) * scale).toInt().coerceAtLeast(0)
        // Hide the browser's visual overlay while a frontend modal is open,
        // without collapsing the website viewport or destroying its profile.
        if (w == 0 || h == 0) {
            activeId?.let { sessions[it]?.visibility = View.INVISIBLE }
            return
        }
        area = intArrayOf(x, y, w, h)
        activeId?.let { sessions[it]?.let { browser -> attachBounds(browser) } }
    }
    private fun attachBounds(browser: WebView) {
        val params = FrameLayout.LayoutParams(area[2], area[3]);params.leftMargin=area[0];params.topMargin=area[1]
        browser.layoutParams = params
        browser.visibility = View.VISIBLE
    }
    private fun hide() {
        activeId?.let { id ->
            popupOwners.filterValues { it==id }.keys.toList().forEach { closePopup(it) }
            sessions[id]?.let { if (it.parent == root) root.removeView(it) }
        }
        activeId = null
    }
    private fun fillSavedLogin(account:String,view:WebView,auto:Boolean,
                               requestId:String?,reply:JavaScriptReplyProxy?) {
        try {
            val current=view.url ?: error("Website not loaded")
            val secret=passwords.forPage(current,auto)
            if(secret==null){
                if(requestId!=null&&reply!=null)respond(reply,requestId,JSONObject()
                    .put("filled",false).put("reason","no_matching_saved_login"))
                return
            }
            check(passwords.origin(current)==passwords.origin(view.url?:"")){"Login origin changed"}
            view.evaluateJavascript(passwords.fillScript(secret)){ output ->
                if(requestId!=null&&reply!=null) {
                    try{respond(reply,requestId,JSONObject(output))}
                    catch(e:Exception){respond(reply,requestId,null,"Autofill: "+e.message)}
                }
            }
        }catch(e:Exception){
            if(requestId!=null&&reply!=null)respond(reply,requestId,null,
                "Autofill unavailable: "+(e.message?:"browser error"))
        }
    }
    private fun dispatch(id: String, method: String, args: JSONObject, reply: JavaScriptReplyProxy) {
        when (method) {
            "backendStatus" -> backendCall(id,"bridge.capabilities",JSONObject(),reply,true)
            "backendRequest" -> backendCall(id,args.getString("operation"),
                args.optJSONObject("payload")?:JSONObject(),reply)
            "status" -> respond(reply,id,JSONObject().put("schema",CONTRACT).put("host","android")
                .put("browserOpen",activeId!=null).put("accountId",activeId)
                .put("multiProfile",WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE))
                .put("mode","browser_controls_available"))
            "vaultStatus" -> respond(reply,id,passwords.status())
            "vaultList" -> respond(reply,id,passwords.list())
            "vaultSave" -> respond(reply,id,passwords.save(args.getString("url"),
                args.getString("username"),args.getString("password"),args.optBoolean("autofill",true)))
            "vaultDelete" -> respond(reply,id,passwords.delete(args.getString("origin")))
            "vaultFill" -> {
                val account=accountId(args.getString("accountId"))
                fillSavedLogin(account,activeBrowser(account),false,id,reply)
            }
            "downloads" -> respond(reply,id,JSONObject().put("items",JSONArray()))
            "browserBounds" -> { bounds(args);respond(reply,id,JSONObject().put("ok",true)) }
            "hideBrowser" -> { hide();respond(reply,id,JSONObject().put("ok",true)) }
            "showBrowser" -> {
                val account = accountId(args.getString("accountId"));val address = safeUrl(args.getString("url"))
                val browser=currentBrowser(account)
                if (activeId != account) hide()
                activeId=account
                if (browser.parent != root) root.addView(browser)
                attachBounds(browser)
                // Account inspection must not discard a loaded same-origin wallet or statement.
                val preserve = args.optBoolean("preserveSameOrigin",false) && try {
                    val existing=URI(browser.url ?: "")
                    val target=URI(address)
                    fun portOf(uri:URI)=if(uri.port>=0)uri.port else if(uri.scheme.equals("https",true))443 else 80
                    existing.scheme.equals(target.scheme,true) &&
                        existing.host?.equals(target.host,true)==true && portOf(existing)==portOf(target)
                } catch(_:Exception) {false}
                if (!preserve && (requested[account] != address || browser.url == null)) {
                    requested[account]=address;browser.loadUrl(address)
                }
                respond(reply,id,JSONObject().put("ok",true).put("accountId",account).put("url",address)
                    .put("profile","isolated persistent WebView profile"))
            }
            "back" -> { activeId?.let{if(sessions[it]?.canGoBack()==true)sessions[it]?.goBack()};respond(reply,id,JSONObject().put("ok",true)) }
            "forward" -> {activeId?.let{if(sessions[it]?.canGoForward()==true)sessions[it]?.goForward()};respond(reply,id,JSONObject().put("ok",true))}
            "reload" -> {activeId?.let{sessions[it]?.reload()};respond(reply,id,JSONObject().put("ok",true))}
            "snapshot" -> {
                val account=accountId(args.getString("accountId"));val browser=activeBrowser(account)
                browser.evaluateJavascript(snapshotScript) { response ->
                    try {
                        val parsed=JSONTokener(response).nextValue()
                        val data=if(parsed is JSONObject)parsed else JSONObject(parsed.toString())
                        data.put("accountId",account).put("contract",CONTRACT)
                        data.put("source",JSONObject().put("type",CONTRACT).put("accountId",account)
                            .put("url",data.optString("url")).put("observedAt",data.optString("observedAt"))
                            .put("verification","candidate_only").put("evidenceOrigin","visible_dom"))
                        respond(reply,id,data)
                    } catch(e:Exception) {respond(reply,id,null,"Snapshot parse failed: "+e.message)}
                }
            }
            "inspectDOM" -> {
                val account=accountId(args.getString("accountId"));val browser=activeBrowser(account)
                val script="""(() => {const nodes=[];for(const el of document.querySelectorAll('a,button,input,select,textarea,[role=button]')){
                  if(nodes.length>=250)break;if(!el.getClientRects().length)continue;const type=(el.type||'').toLowerCase();
                  if(/password|hidden|file/.test(type)||/pass|token|secret|otp|card/i.test(el.name||''))continue;
                  nodes.push({tag:el.tagName.toLowerCase(),type,text:(el.innerText||el.getAttribute('aria-label')||'').slice(0,130)});
                  }return {url:location.href,title:document.title,nodes};})()"""
                browser.evaluateJavascript(script){ response ->
                    try {respond(reply,id,JSONObject(response).put("accountId",account).put("schema",CONTRACT))}
                    catch(e:Exception){respond(reply,id,null,"DOM parse failed: "+e.message)}
                }
            }
            "inspectNetwork" -> {
                val account=accountId(args.getString("accountId"));activeBrowser(account)
                val list=network[account];val records=JSONArray()
                if(list!=null)synchronized(list){list.takeLast(50).forEach{records.put(it)}}
                respond(reply,id,JSONObject().put("schema",CONTRACT).put("accountId",account).put("records",records)
                    .put("metadataOnly",true).put("observedAt",Instant.now().toString()))
            }
            "screenshot" -> {
                val account=accountId(args.getString("accountId"));val browser=activeBrowser(account)
                val w=browser.width.coerceAtLeast(1);val h=browser.height.coerceAtLeast(1)
                require(w*h <= 4_000_000) {"Screenshot dimensions exceed limit"}
                val bitmap=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888)
                browser.draw(Canvas(bitmap));val bytes=ByteArrayOutputStream();bitmap.compress(Bitmap.CompressFormat.PNG,85,bytes);bitmap.recycle()
                val encoded=Base64.encodeToString(bytes.toByteArray(),Base64.NO_WRAP)
                respond(reply,id,JSONObject().put("schema",CONTRACT).put("accountId",account)
                    .put("observedAt",Instant.now().toString()).put("mimeType","image/png")
                    .put("dataUrl","data:image/png;base64,"+encoded))
            }
            "action" -> {
                val account=accountId(args.getString("accountId"));val browser=activeBrowser(account)
                val type=args.getString("type")
                if(type=="navigate") {
                    val address=safeUrl(args.getString("url"));browser.loadUrl(address)
                    respond(reply,id,JSONObject().put("ok",true).put("accountId",account).put("type",type))
                } else if(type=="scroll") {
                    val dy=args.optInt("pixels").coerceIn(-1500,1500)
                    browser.scrollBy(0,(dy*resources.displayMetrics.density).toInt())
                    respond(reply,id,JSONObject().put("ok",true).put("type",type))
                } else if(type=="click" || type=="fill") {
                    val selector=args.getString("selector")
                    require(selector.length in 1..512) {"Invalid selector"}
                    val value=args.optString("text")
                    require(type!="fill" || value.length<=4096) {"Input too long"}
                    val script="""(() => {const el=document.querySelector(${JSONObject.quote(selector)});
                      if(!el||!el.getClientRects().length)return {ok:false,reason:'not_visible'};
                      if(${JSONObject.quote(type)}==='click'){
                        const href=el.closest('a[href]')?.getAttribute('href')||'';
                        if(/^javascript:|^data:|^file:/i.test(href))return {ok:false,reason:'unsafe_navigation'};
                      }
                      if(${JSONObject.quote(type)}==='fill'){
                        if(!['INPUT','TEXTAREA','SELECT'].includes(el.tagName)||el.type==='file')return {ok:false,reason:el.type==='file'?'file_picker_required':'unsupported_input'};
                        const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:el.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;
                        const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;
                        if(!setter)return {ok:false,reason:'input_unavailable'};
                        setter.call(el,${JSONObject.quote(value)});el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
                      }else el.click();return {ok:true};})()"""
                    browser.evaluateJavascript(script) { response ->
                        try {val result=JSONObject(response);result.put("schema",CONTRACT).put("accountId",account)
                            .put("id",java.util.UUID.randomUUID().toString()).put("observedAt",Instant.now().toString());respond(reply,id,result)}
                        catch(e:Exception) {respond(reply,id,null,"Action failed: "+e.message)}
                    }
                } else error("Unsupported browser operation")
            }
            "clearSession" -> {
                val account=accountId(args.getString("accountId"))
                if(activeId==account)hide()
                popupOwners.filterValues{it==account}.keys.toList().forEach { closePopup(it) }
                val web=sessions.remove(account);requested.remove(account)
                val profile=if(WebViewFeature.isFeatureSupported(WebViewFeature.MULTI_PROFILE))
                    (web?.let{WebViewCompat.getProfile(it)} ?: ProfileStore.getInstance().getOrCreateProfile(profileName(account)))
                    else null
                if (web!=null){if(web.parent==root)root.removeView(web);web.stopLoading();web.destroy()}
                if(profile==null)throw IllegalStateException("Isolated WebView profile unavailable")
                profile.cookieManager.removeAllCookies {
                    try {
                        profile.webStorage.deleteAllData();profile.cookieManager.flush()
                        network.remove(account)
                        respond(reply,id,JSONObject().put("ok",true).put("accountId",account)
                            .put("localSessionCleared",true).put("serverRevocationNotGuaranteed",true))
                    }catch(e:Exception){respond(reply,id,null,"Cookie cleanup failed: "+e.message)}
                }
            }
            "openExternal" -> {
                val url=safeUrl(args.getString("url"))
                startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(url)))
                respond(reply,id,JSONObject().put("ok",true))
            }
            else -> error("Unsupported native method")
        }
    }

    override fun onRequestPermissionsResult(requestCode:Int, permissions:Array<out String>, grantResults:IntArray){
        super.onRequestPermissionsResult(requestCode,permissions,grantResults)
        if(requestCode==WEBSITE_PERMISSION_REQUEST){
            val website=pendingWebPermission
            pendingWebPermission=null
            if(website!=null){
                if(grantResults.isNotEmpty() && grantResults.all{it==PackageManager.PERMISSION_GRANTED})
                    website.grant(website.resources)
                else website.deny()
            }
        }
    }
    override fun onSaveInstanceState(outState: Bundle) { ui.saveState(outState);super.onSaveInstanceState(outState) }
    @Deprecated("Browser navigation uses built-in back handling for this development host")
    override fun onBackPressed() {
        if(popupOwners.isNotEmpty()){
            closePopup(popupOwners.keys.last())
            return
        }
        val current=activeId?.let{sessions[it]}
        if(current?.canGoBack()==true)current.goBack()
        else if(activeId!=null)hide()
        else if(ui.canGoBack())ui.goBack()
        else super.onBackPressed()
    }
    override fun onStop() {
        sessions.values.forEach { browser ->
            try { WebViewCompat.getProfile(browser).cookieManager.flush() }
            catch (_: Exception) {}
        }
        super.onStop()
    }
    override fun onDestroy() {
        backendWorker.shutdown()
        popupOwners.keys.toList().forEach { closePopup(it) }
        sessions.values.forEach { if(it.parent==root)root.removeView(it);it.destroy() }
        sessions.clear();ui.destroy();super.onDestroy()
    }
}

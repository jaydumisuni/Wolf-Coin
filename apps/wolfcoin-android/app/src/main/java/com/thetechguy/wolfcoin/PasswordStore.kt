package com.thetechguy.wolfcoin

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.net.URI
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class PasswordStore(private val context:Context) {
    companion object {
        private const val ALIAS="wolfcoin-passwords-aes-v1"
        private const val FILE="wolfcoin_vault_1"
    }
    private val prefs by lazy {context.getSharedPreferences(FILE,Context.MODE_PRIVATE)}
    private fun key(): SecretKey {
        val keystore=KeyStore.getInstance("AndroidKeyStore")
        keystore.load(null)
        val existing=keystore.getKey(ALIAS,null) as? SecretKey
        if(existing!=null)return existing
        val generated=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore")
        val spec=KeyGenParameterSpec.Builder(ALIAS,KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
        generated.init(spec)
        return generated.generateKey()
    }
    fun origin(url:String):String {
        val u=URI(url)
        require(u.userInfo==null && !u.host.isNullOrBlank()){"Invalid site origin"}
        val debug=(context.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE)!=0
        val host=u.host.lowercase()
        val loopback=host=="localhost"||host=="127.0.0.1"||host=="10.0.2.2"
        require(u.scheme.equals("https",true)||(debug&&loopback&&u.scheme.equals("http",true))) {
            "Password vault requires HTTPS"
        }
        require(host!="appassets.androidplatform.net"){"Application UI is not a password target"}
        val port=if(u.port<0||(u.scheme.equals("https",true)&&u.port==443)||(u.scheme.equals("http",true)&&u.port==80))"" else ":${u.port}"
        return u.scheme.lowercase()+"://"+host+port
    }
    private fun seal(json:JSONObject):String {
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE,key())
        val bytes=cipher.doFinal(json.toString().toByteArray(Charsets.UTF_8))
        return Base64.encodeToString(cipher.iv+bytes,Base64.NO_WRAP)
    }
    private fun open(cipherText:String):JSONObject {
        val bytes=Base64.decode(cipherText,Base64.NO_WRAP)
        require(bytes.size>28){"Encrypted password record is invalid"}
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,bytes.copyOfRange(0,12)))
        return JSONObject(String(cipher.doFinal(bytes.copyOfRange(12,bytes.size)),Charsets.UTF_8))
    }
    fun status():JSONObject {
        key()
        return JSONObject().put("available",true).put("backend","AndroidKeyStore AES-GCM")
            .put("plaintextFallback",false)
    }
    fun list():JSONObject {
        val records=JSONArray()
        prefs.all.entries.sortedBy { it.key }.take(300).forEach { (host,raw) ->
            if(raw !is String)return@forEach
            val rec=open(raw)
            records.put(JSONObject().put("origin",host).put("username",rec.getString("username"))
                .put("autofill",rec.optBoolean("autofill",false))
                .put("updatedAt",rec.optString("updatedAt")))
        }
        return JSONObject().put("items",records)
    }
    fun save(url:String,username:String,password:String,autofill:Boolean):JSONObject {
        val host=origin(url)
        require(username.isNotBlank()&&username.length<=128){"Invalid username"}
        require(password.isNotEmpty()&&password.length<=4096){"Invalid password"}
        require(prefs.contains(host)||prefs.all.size<300){"Password manager is full"}
        val record=JSONObject().put("username",username.trim()).put("password",password)
            .put("autofill",autofill).put("updatedAt",java.time.Instant.now().toString())
        check(prefs.edit().putString(host,seal(record)).commit()){"Password could not be saved"}
        return JSONObject().put("ok",true).put("origin",host).put("autofill",autofill)
    }
    fun delete(origin:String):JSONObject {
        val host=origin(origin)
        val found=prefs.contains(host)
        if(found)check(prefs.edit().remove(host).commit()){"Password could not be deleted"}
        return JSONObject().put("ok",true).put("deleted",found).put("origin",host)
    }
    fun forPage(url:String,onlyAuto:Boolean):JSONObject? {
        val host=origin(url)
        val raw=prefs.getString(host,null) ?: return null
        val record=open(raw)
        record.put("origin",host)
        return if(onlyAuto&&!record.optBoolean("autofill",false))null else record
    }
    fun fillScript(record:JSONObject):String {
        val username=JSONObject.quote(record.getString("username"))
        val password=JSONObject.quote(record.getString("password"))
        val origin=JSONObject.quote(record.getString("origin"))
        return """(()=>{if(location.origin!==$origin)return {filled:false,reason:'origin_changed'};const vis=e=>e&&!e.disabled&&!e.readOnly&&e.getClientRects().length>0;
          const pass=[...document.querySelectorAll('input[type=password]')].find(vis);
          if(!pass)return {filled:false,reason:'no_password_field'};
          const form=pass.closest('form')||document;
          const user=[...form.querySelectorAll('input')].find(e=>vis(e)&&e!==pass&&
             /^(text|email|tel|search)$/.test(e.type)&&
             !/otp|one.?time|two.?factor|captcha|verification|card|cvv/i.test(
               [e.name,e.id,e.autocomplete,e.placeholder].join(' ')));
          const set=(e,v)=>{const f=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')?.set;
             if(!f)return;f.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));
             e.dispatchEvent(new Event('change',{bubbles:true}));};
          if(user)set(user,$username);set(pass,$password);
          return {filled:true,usernameFilled:!!user,passwordFilled:true,submitted:false};})()"""
    }
}

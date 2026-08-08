package com.moneylogapp

import android.content.ComponentName
import android.content.Intent
import android.provider.Settings
import android.text.TextUtils
import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule

class NotificationModule(private val reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName() = "MoneyLogNotificationModule"

    @ReactMethod
    fun isServiceEnabled(promise: Promise) {
        val cn = ComponentName(reactContext, MoneyLogNotificationService::class.java)
        val flat = Settings.Secure.getString(
            reactContext.contentResolver,
            "enabled_notification_listeners"
        )
        val enabled = !TextUtils.isEmpty(flat) && flat.contains(cn.flattenToString())
        promise.resolve(enabled)
    }

    @ReactMethod
    fun openNotificationSettings() {
        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        reactContext.startActivity(intent)
    }

    // 이벤트 전송은 NotificationListenerService에서 직접 처리
    @ReactMethod
    fun addListener(eventName: String) {}

    @ReactMethod
    fun removeListeners(count: Int) {}
}

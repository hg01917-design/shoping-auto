package com.moneylogapp

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.facebook.react.ReactApplication
import com.facebook.react.bridge.Arguments
import com.facebook.react.modules.core.DeviceEventManagerModule

class MoneyLogNotificationService : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val extras = sbn.notification.extras
        val title = extras.getString("android.title") ?: ""
        val text = extras.getCharSequence("android.text")?.toString() ?: ""

        val params = Arguments.createMap().apply {
            putString("packageName", sbn.packageName)
            putString("title", title)
            putString("text", text)
            putDouble("timestamp", sbn.postTime.toDouble())
        }

        val reactApp = applicationContext as? ReactApplication ?: return
        reactApp.reactNativeHost.reactInstanceManager
            .currentReactContext
            ?.getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
            ?.emit("onNotificationReceived", params)
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {}
}

package com.hitsz.autonet.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.hitsz.autonet.R
import com.hitsz.autonet.ui.MainActivity
import com.hitsz.autonet.utils.LoginManager
import com.hitsz.autonet.utils.NetworkChecker
import com.hitsz.autonet.utils.PreferencesManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Foreground service for network monitoring and auto-login
 * Mirrors the Python daemon functionality
 */
class NetworkMonitorService : Service() {
    
    private val serviceScope = CoroutineScope(Dispatchers.Default + Job())
    private lateinit var networkChecker: NetworkChecker
    private lateinit var loginManager: LoginManager
    private lateinit var preferencesManager: PreferencesManager
    private lateinit var notificationManager: NotificationManager
    
    companion object {
        private const val TAG = "NetworkMonitorService"
        private const val NOTIFICATION_CHANNEL_ID = "hitsz_autonet_channel"
        private const val NOTIFICATION_ID = 1
        private const val CHECK_INTERVAL_MS = 60000L // 60 seconds
    }
    
    override fun onCreate() {
        super.onCreate()
        networkChecker = NetworkChecker(this)
        loginManager = LoginManager(this)
        preferencesManager = PreferencesManager(this)
        notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        
        createNotificationChannel()
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.i(TAG, "Service started")
        
        // Start foreground service
        val notification = createNotification("Monitoring network...", false)
        startForeground(NOTIFICATION_ID, notification)
        
        // Start monitoring loop
        serviceScope.launch {
            monitorNetwork()
        }
        
        return START_STICKY
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onDestroy() {
        super.onDestroy()
        Log.i(TAG, "Service stopped")
    }
    
    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            NOTIFICATION_CHANNEL_ID,
            "Network Monitor",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "HITSZ Network Auto-Login Monitor"
            setShowBadge(false)
        }
        notificationManager.createNotificationChannel(channel)
    }
    
    private fun createNotification(text: String, isError: Boolean): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        
        return NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setContentTitle("HITSZ AutoNet")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingIntent)
            .setOngoing(!isError)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }
    
    private fun updateNotification(text: String, isError: Boolean = false) {
        val notification = createNotification(text, isError)
        notificationManager.notify(NOTIFICATION_ID, notification)
    }
    
    private fun sendUserNotification(title: String, message: String) {
        val notification = NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()
        
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }
    
    private suspend fun monitorNetwork() {
        val username = preferencesManager.username.first()
        val password = preferencesManager.password.first()
        
        if (username.isBlank() || password.isBlank()) {
            Log.e(TAG, "Credentials not configured")
            updateNotification("Please configure credentials", true)
            return
        }
        
        Log.i(TAG, "Starting network monitoring loop")
        
        while (serviceScope.isActive) {
            try {
                if (!networkChecker.checkInternet()) {
                    Log.i(TAG, "Internet unavailable. Initiating login...")
                    updateNotification("Network lost. Attempting login...")
                    sendUserNotification("HITSZ Net", "Network lost. Attempting login...")
                    
                    if (loginManager.login(username, password)) {
                        Log.i(TAG, "Login successful")
                        sendUserNotification("HITSZ Net", "Login successful. You are back online.")
                        
                        // Double check connectivity
                        delay(2000)
                        if (networkChecker.checkInternet()) {
                            Log.i(TAG, "Connectivity verified")
                            updateNotification("Connected - Monitoring...")
                        } else {
                            Log.w(TAG, "Login reported success but connectivity check failed")
                            updateNotification("Login unclear - Retrying...")
                        }
                    } else {
                        Log.e(TAG, "Login failed")
                        sendUserNotification("HITSZ Net", "Login failed. Will retry.")
                        updateNotification("Login failed - Retrying...")
                    }
                } else {
                    Log.d(TAG, "Connectivity OK")
                    updateNotification("Connected - Monitoring...")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Monitor loop error: ${e.message}", e)
            }
            
            delay(CHECK_INTERVAL_MS)
        }
    }
}

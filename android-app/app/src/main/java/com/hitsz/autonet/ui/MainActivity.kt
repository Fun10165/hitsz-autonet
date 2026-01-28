package com.hitsz.autonet.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.google.android.material.switchmaterial.SwitchMaterial
import com.google.android.material.textfield.TextInputEditText
import com.hitsz.autonet.R
import com.hitsz.autonet.service.NetworkMonitorService
import com.hitsz.autonet.utils.PreferencesManager
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/**
 * Main activity for configuring the app
 */
class MainActivity : AppCompatActivity() {
    
    private lateinit var preferencesManager: PreferencesManager
    private lateinit var usernameInput: TextInputEditText
    private lateinit var passwordInput: TextInputEditText
    private lateinit var autoStartSwitch: SwitchMaterial
    private lateinit var saveButton: MaterialButton
    private lateinit var startServiceButton: MaterialButton
    private lateinit var stopServiceButton: MaterialButton
    
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            Toast.makeText(this, "Notification permission granted", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "Notification permission denied", Toast.LENGTH_SHORT).show()
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        preferencesManager = PreferencesManager(this)
        
        initViews()
        loadPreferences()
        setupListeners()
        requestNotificationPermission()
    }
    
    private fun initViews() {
        usernameInput = findViewById(R.id.usernameInput)
        passwordInput = findViewById(R.id.passwordInput)
        autoStartSwitch = findViewById(R.id.autoStartSwitch)
        saveButton = findViewById(R.id.saveButton)
        startServiceButton = findViewById(R.id.startServiceButton)
        stopServiceButton = findViewById(R.id.stopServiceButton)
    }
    
    private fun loadPreferences() {
        lifecycleScope.launch {
            val username = preferencesManager.username.first()
            val password = preferencesManager.password.first()
            val autoStart = preferencesManager.autoStart.first()
            
            usernameInput.setText(username)
            passwordInput.setText(password)
            autoStartSwitch.isChecked = autoStart
        }
    }
    
    private fun setupListeners() {
        saveButton.setOnClickListener {
            saveCredentials()
        }
        
        startServiceButton.setOnClickListener {
            startMonitoringService()
        }
        
        stopServiceButton.setOnClickListener {
            stopMonitoringService()
        }
        
        autoStartSwitch.setOnCheckedChangeListener { _, isChecked ->
            lifecycleScope.launch {
                preferencesManager.setAutoStart(isChecked)
            }
        }
    }
    
    private fun saveCredentials() {
        val username = usernameInput.text.toString().trim()
        val password = passwordInput.text.toString().trim()
        
        if (username.isBlank() || password.isBlank()) {
            Toast.makeText(this, "Please enter both username and password", Toast.LENGTH_SHORT).show()
            return
        }
        
        lifecycleScope.launch {
            preferencesManager.saveCredentials(username, password)
            Toast.makeText(this@MainActivity, "Credentials saved", Toast.LENGTH_SHORT).show()
        }
    }
    
    private fun startMonitoringService() {
        val intent = Intent(this, NetworkMonitorService::class.java)
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
        
        Toast.makeText(this, "Service started", Toast.LENGTH_SHORT).show()
    }
    
    private fun stopMonitoringService() {
        val intent = Intent(this, NetworkMonitorService::class.java)
        stopService(intent)
        Toast.makeText(this, "Service stopped", Toast.LENGTH_SHORT).show()
    }
    
    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            when {
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED -> {
                    // Permission already granted
                }
                else -> {
                    requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }
        }
    }
}

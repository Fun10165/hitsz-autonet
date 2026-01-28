package com.hitsz.autonet.utils

import android.content.Context
import android.util.Log
import android.webkit.ConsoleMessage
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import kotlin.coroutines.resume

/**
 * HITSZ Network Login Manager
 * Mirrors the Python login() function using WebView for JavaScript execution
 * 
 * ENHANCED DEBUG VERSION with comprehensive logging
 */
class LoginManager(private val context: Context) {
    
    companion object {
        private const val TAG = "LoginManager"
        private const val LOGIN_URL = "http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2"
        private const val TIMEOUT_MS = 30000L
        private const val PAGE_LOAD_DELAY = 2000L
        private const val LOGIN_SUBMIT_DELAY = 3000L
    }
    
    /**
     * Perform login using credentials
     * Returns true if successful, false otherwise
     */
    suspend fun login(username: String, password: String): Boolean = withContext(Dispatchers.Main) {
        if (username.isBlank() || password.isBlank()) {
            Log.e(TAG, "Username or password not set")
            return@withContext false
        }
        
        Log.i(TAG, "========== LOGIN ATTEMPT START ==========")
        Log.i(TAG, "Username: $username")
        Log.i(TAG, "Login URL: $LOGIN_URL")
        
        return@withContext try {
            withTimeout(TIMEOUT_MS) {
                performLogin(username, password)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Login error: ${e.message}", e)
            Log.e(TAG, "========== LOGIN ATTEMPT FAILED ==========")
            false
        }
    }
    
    private suspend fun performLogin(username: String, password: String): Boolean = suspendCancellableCoroutine { continuation ->
        var loginSuccess = false
        var pageLoaded = false
        
        val webView = WebView(context).apply {
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                databaseEnabled = true
                cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
                userAgentString = "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
                
                Log.d(TAG, "WebView settings configured")
                Log.d(TAG, "User-Agent: $userAgentString")
            }
            
            // Enable console logging for JavaScript debugging
            webChromeClient = object : WebChromeClient() {
                override fun onConsoleMessage(consoleMessage: ConsoleMessage): Boolean {
                    Log.d(TAG, "WebView Console [${consoleMessage.messageLevel()}]: ${consoleMessage.message()} -- From line ${consoleMessage.lineNumber()} of ${consoleMessage.sourceId()}")
                    return true
                }
            }
            
            webViewClient = object : WebViewClient() {
                override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                    super.onPageStarted(view, url, favicon)
                    Log.d(TAG, "Page loading started: $url")
                }
                
                override fun onPageFinished(view: WebView?, url: String?) {
                    super.onPageFinished(view, url)
                    Log.i(TAG, "Page loaded successfully: $url")
                    
                    if (pageLoaded) {
                        Log.d(TAG, "Page already processed, ignoring duplicate onPageFinished")
                        return
                    }
                    pageLoaded = true
                    
                    // Wait for Vue.js app to render (mobile page uses Vue)
                    Log.d(TAG, "Waiting ${PAGE_LOAD_DELAY}ms for dynamic content to load...")
                    
                    android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                        if (!loginSuccess) {
                            Log.d(TAG, "Dynamic content should be ready, checking page structure...")
                            performLoginAttempt(view)
                        } else {
                            Log.d(TAG, "Login already completed, skipping")
                        }
                    }, PAGE_LOAD_DELAY)
                }
                
                private fun performLoginAttempt(view: WebView?) {
                    // Step 1: Check page structure
                    view?.evaluateJavascript("""
                        (function() {
                            try {
                                var result = {
                                    url: window.location.href,
                                    title: document.title,
                                    hasConfig: typeof window.CONFIG !== 'undefined',
                                    config: window.CONFIG ? JSON.stringify(window.CONFIG) : null,
                                    hasUsernameField: !!document.getElementById('username'),
                                    hasPasswordField: !!document.getElementById('password'),
                                    hasLoginButton: !!document.getElementById('login-account')
                                };
                                return JSON.stringify(result);
                            } catch(e) {
                                return JSON.stringify({error: e.toString()});
                            }
                        })();
                    """.trimIndent()) { pageInfoJson ->
                        Log.i(TAG, "Page info: $pageInfoJson")
                        
                        // Parse and check if already logged in
                        if (pageInfoJson != null && pageInfoJson.contains("\"page\":\"success\"")) {
                            Log.i(TAG, "Already logged in detected")
                            loginSuccess = true
                            if (continuation.isActive) {
                                continuation.resume(true)
                            }
                            view?.destroy()
                            return@evaluateJavascript
                        }
                        
                        val formDetected = pageInfoJson?.contains("true") == true
                        Log.d(TAG, "Form detected: $formDetected, raw: ${pageInfoJson?.take(100)}")
                        
                        Log.i(TAG, "Login form found! Proceeding with login...")
                        Log.i(TAG, "Filling login form...")
                        val loginScript = """
                            (function() {
                                try {
                                    // Try PC version selectors first
                                    var usernameField = document.getElementById('username');
                                    var passwordField = document.getElementById('password');
                                    var loginBtn = document.getElementById('login-account');
                                    
                                    // If not found, try mobile version selectors
                                    if (!usernameField) usernameField = document.querySelector('input[name="username"]') || document.querySelector('input[type="text"]');
                                    if (!passwordField) passwordField = document.querySelector('input[name="password"]') || document.querySelector('input[type="password"]');
                                    if (!loginBtn) loginBtn = document.querySelector('button[type="submit"]') || document.querySelector('.login-btn') || document.querySelector('button');
                                    
                                    if (!usernameField) return {status: 'ERROR', message: 'Username field not found (tried multiple selectors)'};
                                    if (!passwordField) return {status: 'ERROR', message: 'Password field not found (tried multiple selectors)'};
                                    if (!loginBtn) return {status: 'ERROR', message: 'Login button not found (tried multiple selectors)'};
                                    
                                    console.log('Form elements found: username=' + usernameField.id + ', password=' + passwordField.id + ', button=' + loginBtn.tagName);
                                    
                                    // Fill credentials
                                    usernameField.value = '$username';
                                    passwordField.value = '$password';
                                    
                                    // Trigger input events for frameworks that listen to them
                                    var inputEvent = new Event('input', { bubbles: true });
                                    usernameField.dispatchEvent(inputEvent);
                                    passwordField.dispatchEvent(inputEvent);
                                    
                                    console.log('Credentials filled, clicking login button...');
                                    
                                    // Click login button
                                    loginBtn.click();
                                    
                                    return {status: 'SUBMITTED', message: 'Login form submitted'};
                                } catch(e) {
                                    return {status: 'ERROR', message: e.toString()};
                                }
                            })();
                        """.trimIndent()
                        
                        view?.evaluateJavascript(loginScript) { submitResult ->
                            Log.i(TAG, "Login submit result: $submitResult")
                            
                            Log.d(TAG, "Waiting ${LOGIN_SUBMIT_DELAY}ms for login to process...")
                            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                                Log.i(TAG, "Verifying login via network connectivity check...")
                                view?.destroy()
                                
                                Thread {
                                    try {
                                        val url = java.net.URL("http://www.baidu.com")
                                        val conn = url.openConnection() as java.net.HttpURLConnection
                                        conn.connectTimeout = 5000
                                        conn.readTimeout = 5000
                                        conn.instanceFollowRedirects = false
                                        val responseCode = conn.responseCode
                                        val finalUrl = conn.url.toString()
                                        conn.disconnect()
                                        
                                        loginSuccess = responseCode == 200 && !finalUrl.contains("net.hitsz.edu.cn")
                                        
                                        android.os.Handler(android.os.Looper.getMainLooper()).post {
                                            if (loginSuccess) {
                                                Log.i(TAG, "✓ Login successful! Network is accessible.")
                                            } else {
                                                Log.e(TAG, "✗ Login may have failed - network still redirecting")
                                            }
                                            Log.i(TAG, "========== LOGIN ATTEMPT END ==========")
                                            
                                            if (continuation.isActive) {
                                                continuation.resume(loginSuccess)
                                            }
                                        }
                                    } catch (e: Exception) {
                                        Log.e(TAG, "Verification network check failed: ${e.message}")
                                        android.os.Handler(android.os.Looper.getMainLooper()).post {
                                            if (continuation.isActive) {
                                                continuation.resume(false)
                                            }
                                        }
                                    }
                                }.start()
                            }, LOGIN_SUBMIT_DELAY)
                        }
                    }
                }
                
                override fun onReceivedError(view: WebView?, errorCode: Int, description: String?, failingUrl: String?) {
                    super.onReceivedError(view, errorCode, description, failingUrl)
                    Log.e(TAG, "WebView error: code=$errorCode, description=$description, url=$failingUrl")
                    
                    if (!loginSuccess && continuation.isActive) {
                        continuation.resume(false)
                        view?.destroy()
                    }
                }
                
                override fun onReceivedHttpError(
                    view: WebView?,
                    request: android.webkit.WebResourceRequest?,
                    errorResponse: android.webkit.WebResourceResponse?
                ) {
                    super.onReceivedHttpError(view, request, errorResponse)
                    Log.w(TAG, "HTTP error: ${errorResponse?.statusCode} for ${request?.url}")
                }
            }
        }
        
        continuation.invokeOnCancellation {
            Log.w(TAG, "Login cancelled")
            webView.destroy()
        }
        
        Log.d(TAG, "Loading login page...")
        webView.loadUrl(LOGIN_URL)
    }
}

package com.hitsz.autonet.utils

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Network connectivity checker
 * Mirrors the Python check_internet() function
 */
class NetworkChecker(private val context: Context) {
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .followRedirects(true)
        .build()
    
    companion object {
        private const val TAG = "NetworkChecker"
        private const val CHECK_URL = "http://www.baidu.com"
    }
    
    /**
     * Check if device has network connectivity
     */
    fun isNetworkAvailable(): Boolean {
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
               capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }
    
    /**
     * Check actual internet connectivity by requesting Baidu
     * Returns true if connected to real internet (not captive portal)
     */
    suspend fun checkInternet(): Boolean = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url(CHECK_URL)
                .build()
            
            client.newCall(request).execute().use { response ->
                if (response.code != 200) {
                    Log.i(TAG, "Connectivity check failed: Status ${response.code}")
                    return@withContext false
                }
                
                // Check if we're actually on Baidu (not a captive portal)
                val url = response.request.url.toString()
                val body = response.body?.string() ?: ""
                
                val isBaidu = url.contains("baidu.com") || body.contains("百度")
                
                if (!isBaidu) {
                    Log.i(TAG, "Connectivity check failed: Redirected to $url")
                }
                
                return@withContext isBaidu
            }
        } catch (e: IOException) {
            Log.w(TAG, "Connectivity check error: ${e.message}")
            return@withContext false
        } catch (e: Exception) {
            Log.e(TAG, "Unexpected error during connectivity check", e)
            return@withContext false
        }
    }
}

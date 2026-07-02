# How to Export Facebook Cookies

Facebook downloads require authentication cookies to work properly. Follow these steps:

## Method 1: Using "Get cookies.txt LOCALLY" Extension (Recommended)

### Step 1: Install Browser Extension
- **Chrome/Edge**: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
- **Firefox**: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

### Step 2: Login to Facebook
1. Open your browser
2. Go to https://www.facebook.com
3. **Login with your Facebook account** (very important!)
4. Make sure you can see your feed

### Step 3: Export Cookies
1. **Stay on facebook.com** (don't navigate away)
2. Click the extension icon in your browser toolbar
3. Click "Export" or "Download"
4. A `cookies.txt` file will be downloaded

### Step 4: Move to Data Folder
1. Find your downloaded `cookies.txt` file (usually in Downloads folder)
2. Copy or move it to:
   ```
   C:\Users\Shahid\Documents\GitHub\pythonprojects\VideoTextExtractor\data\cookies.txt
   ```
3. **Important**: Make sure the file is named exactly `cookies.txt` (not `cookies (1).txt`)

## Troubleshooting

### "Download timed out" Error
This means:
- Your cookies are missing or expired
- Facebook is rate-limiting you (wait 10-15 minutes)
- Bad internet connection

**Solution**: Export fresh cookies and try again

### "No cookies.txt found" Warning
- The app can't find your cookies file
- Check the file path: `data\cookies.txt`
- Make sure you're logged into Facebook when exporting

### Cookies Expire
- Facebook cookies expire after a few days/weeks
- If downloads stop working, export fresh cookies
- Don't logout from Facebook after exporting cookies

## Important Notes

✅ **DO:**
- Stay logged into Facebook in your browser
- Re-export cookies if they expire
- Keep cookies.txt file safe (it contains your login session)

❌ **DON'T:**
- Share your cookies.txt file with anyone
- Logout from Facebook after exporting cookies
- Use old/expired cookies

## Test Your Cookies

After placing cookies.txt, try downloading a single Facebook reel to test:
1. Copy any Facebook reel URL
2. Paste in the app
3. Click "Process Now"
4. If it works ✅ your cookies are valid!
5. If it fails ❌ export fresh cookies

---

**Need Help?** Make sure you:
1. Are logged into Facebook in browser
2. Export cookies while ON facebook.com
3. Place cookies.txt in the correct `data` folder
4. The file is named exactly `cookies.txt`

# How to Merge Instagram + Facebook Cookies

You only need **ONE** `cookies.txt` file that contains cookies from BOTH Instagram and Facebook!

## Method 1: Export All Cookies at Once (Easiest)

### Step 1: Login to Both Sites
1. Open your browser
2. Login to **Instagram** in one tab: https://www.instagram.com
3. Login to **Facebook** in another tab: https://www.facebook.com
4. Keep both tabs open

### Step 2: Export Cookies from Instagram
1. Go to the Instagram tab
2. Click the "Get cookies.txt LOCALLY" extension
3. Click Export
4. Save as `instagram_cookies.txt` (rename it)

### Step 3: Export Cookies from Facebook
1. Go to the Facebook tab
2. Click the "Get cookies.txt LOCALLY" extension
3. Click Export
4. Save as `facebook_cookies.txt` (rename it)

### Step 4: Merge the Files
1. Open `instagram_cookies.txt` in Notepad
2. Copy ALL the content
3. Open `facebook_cookies.txt` in Notepad
4. Paste the Instagram content at the END of the Facebook file
5. Save as `cookies.txt`
6. Move to: `C:\Users\Shahid\Documents\GitHub\pythonprojects\VideoTextExtractor\data\cookies.txt`

---

## Method 2: Use Extension's "Export All" Feature (Even Easier!)

### Step 1: Login to Both Sites
1. Open your browser
2. Login to **Instagram**: https://www.instagram.com
3. Login to **Facebook**: https://www.facebook.com
4. Keep both tabs open

### Step 2: Export ALL Cookies
1. Click the "Get cookies.txt LOCALLY" extension icon
2. Look for "Export All Cookies" or just export while on any tab
3. The extension will export cookies from ALL sites you're logged into!
4. Save the file as `cookies.txt`
5. Move to: `C:\Users\Shahid\Documents\GitHub\pythonprojects\VideoTextExtractor\data\cookies.txt`

---

## Method 3: Manual Merge (If You Already Have Instagram Cookies)

If you already have Instagram cookies in `data\cookies.txt`:

### Step 1: Backup Current Cookies
1. Go to: `C:\Users\Shahid\Documents\GitHub\pythonprojects\VideoTextExtractor\data\`
2. Copy `cookies.txt` and rename the copy to `cookies_backup.txt`

### Step 2: Export Facebook Cookies
1. Login to Facebook
2. Export cookies using the extension
3. Save as `facebook_cookies.txt`

### Step 3: Merge Them
1. Open your current `cookies.txt` (Instagram cookies) in Notepad
2. Open `facebook_cookies.txt` in Notepad
3. Copy ALL content from `facebook_cookies.txt`
4. Go to the end of `cookies.txt` and paste the Facebook cookies
5. Save `cookies.txt`
6. Keep it in the `data` folder

**Result**: Your `cookies.txt` now has BOTH Instagram and Facebook cookies!

---

## What the Merged File Looks Like

Your `cookies.txt` will look like this:

```
# Netscape HTTP Cookie File
# Instagram cookies
.instagram.com	TRUE	/	TRUE	1234567890	sessionid	abc123...
.instagram.com	TRUE	/	FALSE	1234567890	csrftoken	xyz789...
.instagram.com	TRUE	/	TRUE	1234567890	ds_user_id	456...

# Facebook cookies
.facebook.com	TRUE	/	TRUE	1234567890	c_user	789...
.facebook.com	TRUE	/	TRUE	1234567890	xs	def456...
.facebook.com	TRUE	/	FALSE	1234567890	datr	ghi789...
```

Both sets of cookies can exist in the same file!

---

## Testing

After merging, test both platforms:

### Test Instagram:
1. Paste an Instagram reel URL
2. Click "Process Now"
3. Should work ✅

### Test Facebook:
1. Paste a Facebook reel URL
2. Click "Process Now"
3. Should work ✅

---

## Important Notes

✅ **Good to know:**
- One `cookies.txt` file works for ALL platforms (Instagram, Facebook, YouTube, TikTok)
- You can add cookies from as many sites as you want
- The extension exports cookies from the current site only (unless you use "Export All")

⚠️ **Remember:**
- Cookies expire after some time
- If one platform stops working, re-export cookies for that platform and merge again
- Keep both Instagram and Facebook sessions active in your browser

---

## Quick Refresh (When Cookies Expire)

If Instagram works but Facebook doesn't (or vice versa):

1. Export fresh cookies from the broken platform
2. Open your current `cookies.txt`
3. Delete the old cookies for that platform (e.g., all lines with `.facebook.com`)
4. Paste the new cookies at the end
5. Save and test

Done! 🎯

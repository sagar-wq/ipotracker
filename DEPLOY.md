# Putting IPO Radar online for free

## ⭐ Recommended: the full version, with access-code login

What you get: the complete app (live GMP, subscription, Apply/Avoid calls, expert views) at an address like `https://ipo-radar-yourname.streamlit.app`. Visitors see only a **login page** and enter a **10-character code** that you create in the **Admin panel**. You can revoke, extend or reset any code at any time.

Everything below is free and takes about 25 minutes, all in the browser.

### Step 1: GitHub account and repository
1. Sign up at **github.com** (free).
2. **+ → New repository** → name `ipo-radar` → choose **Private** → **Create repository**.
3. Click **"uploading an existing file"**. Extract a fresh copy of `ipo_radar.zip`, open the inner `ipo_radar` folder, select everything inside (Ctrl+A) and drag it onto the page → **Commit changes**.
   Don't upload a `.venv` folder or anything from `data\` of the copy you've been running.

### Step 2: A free "gist" to store codes permanently
Streamlit's free servers wipe their files when the app restarts (about every 12 idle hours), so codes and watchlists are kept in a private GitHub Gist instead.
1. Go to **gist.github.com**.
2. Filename: `access_codes.json` · content: `[]`
3. Click the arrow next to the green button and choose **Create secret gist**.
4. Copy the long ID at the end of the page address, e.g. `https://gist.github.com/yourname/`**`4f9c1e0a7b2d...`**. That's your **GIST_ID**.

### Step 3: A GitHub token so the app can write to that gist
1. github.com → your photo (top right) → **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**.
2. Note: `IPO Radar`. Expiration: **No expiration** (or 1 year, and set a reminder to renew it).
3. Tick only **gist**. Click **Generate token** and copy it (starts with `ghp_`). That's your **GITHUB_TOKEN**. Keep it private.

### Step 4: Deploy on Streamlit Community Cloud
1. Go to **share.streamlit.io** → **Continue with GitHub** → allow access (include your private repo).
2. **Create app → Deploy a public app from GitHub** → Repository `yourname/ipo-radar`, Branch `main`, Main file `app.py`. Pick an address under **App URL**.
3. Open **Advanced settings** → Python **3.12** → paste into **Secrets** (with your own values):
```toml
ADMIN_PASSWORD = "choose-a-strong-admin-password"
SECRET_KEY     = "any-long-random-text-e.g.-k7Qp2vX9mR4tL8wZ"
GITHUB_TOKEN   = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
GIST_ID        = "4f9c1e0a7b2d..."
```
   Optional: `ANTHROPIC_API_KEY = "sk-ant-..."` for the AI notes. Only the admin can use them.
4. Click **Deploy** and wait 2–4 minutes.

### Step 5: Let people in
1. Because the repository is private, Streamlit starts the app as private, which would make visitors sign in to Streamlit too. Open your app's **⋮ → Settings → Sharing** and set **"This app is public"**. The code login page still protects everything.
   (If that option isn't offered, make the GitHub repository public instead. No passwords or tokens are in it; they live only in Streamlit's Secrets.)
2. Open your app → **Admin** (on the login page) → enter your admin password.
3. Go to **🔑 Admin panel** → type a name → choose validity → **Create**. Copy the code shown (e.g. `DJGFV-QUDJH`) and send it with the site link. Codes are shown only once. If one gets lost, use **Reset code**.
4. The admin panel's green "Storage" line should say *GitHub Gist connected*. If it's yellow or red, re-check the token and gist ID.

### Day to day
- **Revoke** switches a code off (the person is logged out on their next page load). **+30 days** extends it, **Reset code** issues a new one, and **Delete** removes it.
- Each person has their **own watchlist**. Expert views you add as admin are shown to everyone.
- To change the admin password, edit Secrets in Streamlit (the app restarts automatically).
- **Updating the app**: upload changed files to the GitHub repo (Add file → Upload files → Commit). Codes and watchlists are untouched.

### Good to know
- **Live data from abroad:** Streamlit's servers are outside India, and some Indian data sites may block them. If the sidebar shows **⚠️ Fetch issues**, the app falls back to its last saved data (or the demo snapshot). Your PC copy is unaffected.
- **Sleep:** after about 12 hours with no visitors the app sleeps. The next visitor clicks "wake up" and waits about 30 seconds.
- **Keep it invitation-only.** The Apply/Avoid calls and the data from InvestorGain/Chittorgarh are fine for you and a private circle. Sharing codes widely (public groups, social media) or charging for access would bring back the SEBI and data-permission issues we discussed.

---

## Other ways to host (password-only, or the permission-free public sheet edition)

You'll get a web address like `https://ipo-radar-yourname.streamlit.app` that opens on any phone or computer. No installing, and your own PC doesn't need to be on.

## First, choose how open it should be

| Mode | Who can see it | Settings (step 4) | Recommended? |
|---|---|---|---|
| **A. Private** | You + people you invite, or anyone with the password | `APP_PASSWORD = "your-password"` | ✅ Full features (live GMP, Apply/Avoid calls) for personal use. |
| **B. Public, permission-free** | Anyone with the link | `DATA_SOURCE = "sheet"`, `SHEET_URL = "<your Google Sheet link>"`, `PUBLIC_MODE = "true"` | ✅ Recommended for a public site. Uses only facts **you** enter from public documents, with no scraping, no GMP, no calls, and a disclaimer. See **SHEET_GUIDE.md**. |
| C. Public with scraped data or calls | Anyone | none | ❌ Needs data permission from InvestorGain/Chittorgarh/NSE, and SEBI registration for Apply/Avoid calls. |

You can run **both A and B**: two apps from the same GitHub repository, each with its own secrets. (Streamlit allows one *private* app per free account, and as many public ones as you like.)

## Step-by-step (about 15 minutes, all in the browser)

### 1. Create a free GitHub account
Go to **github.com** → Sign up.

### 2. Put the app's files on GitHub
1. Click **+** (top right) → **New repository**.
2. Name: `ipo-radar`. Choose **Private** for mode A, or **Public** for mode B. Click **Create repository**.
3. On the next page click **"uploading an existing file"**.
4. Extract a **fresh** copy of `ipo_radar.zip`, open the inner `ipo_radar` folder, select **everything inside** (Ctrl+A) and drag it into the GitHub page. Don't upload a `.venv` folder or a `data\ipo_radar.db` file from the copy you've been running, because they're large or personal.
5. Click **Commit changes**.

> If the `.streamlit` folder didn't upload (some browsers skip folders whose names start with a dot), that's fine. It only sets the colour theme.

### 3. Deploy on Streamlit Community Cloud
1. Go to **share.streamlit.io** → **Continue with GitHub** and allow access.
2. Click **Create app** → **Deploy a public app from GitHub** (the same button works for private repos).
3. Repository: `yourname/ipo-radar` · Branch: `main` · Main file path: `app.py`.
4. Optionally, pick a nice address under **App URL**, e.g. `ipo-radar-sagar`.

### 4. Add your settings (Advanced settings → Secrets)
Before clicking Deploy, open **Advanced settings**. Choose Python **3.11** or **3.12**, then paste the line for your mode into **Secrets**:

Mode A (private, password):
```toml
APP_PASSWORD = "choose-a-strong-password"
```
Mode B (public, permission-free sheet edition; set up the sheet first using SHEET_GUIDE.md):
```toml
DATA_SOURCE = "sheet"
SHEET_URL   = "https://docs.google.com/spreadsheets/d/....../edit?usp=sharing"
PUBLIC_MODE = "true"
```
Optional, for the AI features (anyone using the app will spend your credits, so only do this in mode A):
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Click **Deploy**. The first start takes 2–4 minutes while it installs everything. After that it's live.

### 5. Share it
- Mode A: send people the link and password. For a private GitHub repo you can also use **Share** → invite by email, and then no password is needed. Streamlit allows one private app per free account.
- Mode B: share the link.

## Updating later
Upload changed files to the same GitHub repository (**Add file → Upload files**, then commit). The app picks up the changes within a minute.

## Good to know about free hosting
- **It naps.** With no visitors for about 12 hours the app goes to sleep. The next visitor sees a "wake up" button and waits about 30 seconds.
- **Data may get blocked (mode A only).** The server runs outside India, and some Indian sites block cloud servers. If the sidebar shows **⚠️ Fetch issues**, the app falls back to saved or demo data. Mode B only reads your Google Sheet, so it isn't affected.
- **No permanent storage.** Saved GMP snapshots, watchlists and expert views reset whenever the app restarts. In mode B they're per-visitor anyway.
- **Limits.** The free tier gives roughly 1 GB of memory, which is plenty for this app and a modest number of simultaneous users.

## Alternatives (also free)
- **Hugging Face Spaces**: create a Space → SDK "Streamlit" → upload the same files. Add settings under Settings → Variables and secrets.
- **Render.com** (free web service): build command `pip install -r requirements.txt`, start command `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`.

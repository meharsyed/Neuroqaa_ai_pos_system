# 📱 User Guide — Multi-Language, Printer Options & Reports

A practical guide for shop owners and staff using Phase 5 features.

---

## 🌐 Using Multi-Language (English/Urdu)

### How to Switch Language

1. **Look at the sidebar header** — You'll see a small button: **🌐 EN**
2. **Click the dropdown arrow** — Two options appear:
   - English
   - اردو (Urdu)
3. **Select اردو** — The entire interface switches to Urdu instantly
4. **The change is saved** — Your language choice stays even after closing and reopening the app

### What Gets Translated

✅ **Sidebar Navigation:**
- Dashboard → ڈیش بورڈ
- Products → مصنوعات  
- Checkout → چیک آؤٹ
- Bills → بل
- Reports → رپورٹیں
- Audit → آڈٹ
- Settings → ترتیبات

✅ **Buttons & Actions:**
- Save → محفوظ کریں
- Delete → حذف کریں
- Add → شامل کریں
- Search → تلاش
- Export → رپورٹ نکالیں

✅ **Checkout:**
- All cart labels, payment methods, totals

✅ **Reports:**
- Daily, range, inventory, audit report labels

✅ **Settings:**
- All setting groups (Printer, Receipt, Appearance, etc.)

❌ **NOT Translated (by design):**
- Product names (you entered them in English)
- Shop name
- Custom notes and descriptions
- Numbers and amounts (always numeric)

### RTL (Right-to-Left) Layout

When you select Urdu:
- Text flows from **right to left**
- The layout automatically **mirrors**
- Buttons and menus still work the same way
- **Everything adjusts automatically** — no manual changes needed

### Pro Tip: Multi-Staff Usage

- **Owner:** Sets default language in Settings
- **Cashiers:** Can switch language anytime via the 🌐 EN button
- **Change is permanent** (saved to your browser)
- Each staff member can use their preferred language

---

## 🖨️ Printer Options & Receipt Settings

### Who Can Configure Printers
✅ **Owner/Manager** — Full printer configuration  
❌ **Cashiers/Stock Clerks** — View only

### Accessing Printer Settings

1. Go to **Settings** page
2. Scroll to **Printer Options** section
3. You'll see 3 configuration options

### Option 1: Receipt Template Type

**What is this?**
- Controls how receipt looks when printed
- Affects detail level and formatting

**Options:**
- **Classic** — Standard receipt (basic info)
- **Detailed** — Full receipt with item breakdown
- **Minimal** — Compact, simple receipt

**When to use:**
- Classic: Most common, good for thermal printers
- Detailed: When you want full transaction history
- Minimal: When paper is limited

### Option 2: Page Format

**What is this?**
- Controls the physical size of printed receipt

**Options:**
- **A4** — Standard paper (210×297mm)
- **Letter** — US standard (8.5×11 inches)
- **80mm** — Thermal printer width (58-80mm wide)

**When to use:**
- 80mm: If you have a thermal receipt printer
- A4/Letter: If you print to regular paper via PDF

### Option 3: Thermal Printer Settings

**What is this?**
- Network printer configuration for ESC/POS thermal printers
- IP address and port of your thermal printer

**How to find your printer IP:**
1. Check printer's settings/configuration page
2. Look for "Network Settings" → "IP Address"
3. Or ask your IT team

**How to find port:**
- Default is usually **9100**
- Check printer manual if different

**Example:**
- IP: 192.168.1.100
- Port: 9100

### Testing Printer Configuration

1. **Set printer options as above**
2. **Go to Checkout page**
3. **Create a test sale**
4. **Click Print Receipt**
5. **Watch for:**
   - If thermal printer: Receipt prints to printer
   - If PDF: Receipt PDF downloads to computer
6. **If error:** Check IP/port, ensure printer is on network

---

## 📊 Using Reports & Audit

### Report Types

**1. Daily Report**
- Single day sales
- Item breakdown
- Payment methods used
- Best-selling products
- Access: Audit Reports → Select "Today"

**2. Range Report**
- Custom date range analysis
- Sales trends
- Product performance
- Access: Audit Reports → Select "From" and "To" dates

**3. Inventory Report**
- Current stock levels
- Stock value (cost & selling price)
- Profit margins
- Low-stock items
- Access: Reports menu

**4. Audit Report** (Owner/Manager only)
- All completed sales
- Voided transactions
- Refunds
- Shift reconciliation
- Cash balance verification
- Access: Audit Reports page

### Generating Reports

#### Step 1: Open Audit Reports
1. Click **Audit Reports** in sidebar
2. Page loads with date range filters

#### Step 2: Select Date Range
1. Click **"From" date field**
2. Pick start date (e.g., Aug 1)
3. Click **"To" date field**
4. Pick end date (e.g., Aug 31)
5. Click **Apply** or **View Report**

#### Step 3: View Report
- Summary metrics appear at top
- Detailed sales list shows below
- Each row has: Bill#, DateTime, Amount, Status, Actions

#### Step 4: Export Report

**Export as PDF:**
1. Click **Export PDF** button
2. Professional report downloads
3. Can print or email

**Export as CSV:**
1. Click **Export CSV** button
2. Spreadsheet downloads
3. Open in Excel for analysis

### Understanding Audit Summary

**Example Summary:**
```
Total Completed: 45 sales ........... 87,500 Rs
Total Voided: 2 sales ............... (5,000 Rs)
Total Refunded: 0 ................... 0 Rs
─────────────────────────────────────────
NET SALES: 43 ...................... 82,500 Rs

Cash Reconciliation:
  Opening Float ..................... 5,000 Rs
+ Cash Sales Total .................. 60,000 Rs
─────────────────────────────────────────
= Expected Cash in Drawer ........... 65,000 Rs
- Actual Cash Counted .............. 64,500 Rs
─────────────────────────────────────────
= VARIANCE: -500 Rs (Shortage)
```

**What these mean:**
- **Completed** = normal sales
- **Voided** = sales that were cancelled
- **Refunded** = returns/partial refunds
- **Variance** = difference between expected and actual cash

### Pro Tips for Reports

**Tip 1: Daily Review**
- Check daily report every evening
- Catch discrepancies early
- Print and file for records

**Tip 2: Weekly Analysis**
- Generate weekly report (Mon-Sun)
- Look for trends
- Identify best/worst days

**Tip 3: Monthly Audit**
- Generate full month report
- Compare to previous months
- Share with accountant

**Tip 4: Cash Reconciliation**
- Audit report shows cash variance
- If negative: count cash, find missing amount
- If positive: count cash, find extra amount

---

## ⚙️ Changing Language in Settings

### For Owner/Manager

**Step 1: Go to Settings**
1. Click **Settings** in sidebar

**Step 2: Find Appearance Section**
1. Scroll down to **Appearance**
2. Look for **Language** dropdown

**Step 3: Change Language**
1. Click dropdown
2. Select:
   - **English** (for English POS)
   - **اردو** (for Urdu POS)
3. Click **Save** button

**Step 4: Verify**
1. Refresh page
2. Interface should show in selected language
3. All staff members see this as default

### Effect of Changing Language
- Changes shop-wide default language
- Individual staff can still override with 🌐 EN button
- All new sessions use this language

---

## 🆘 Troubleshooting

### Language Toggle Not Working

**Problem:** 🌐 EN button doesn't appear or dropdown doesn't work

**Solution:**
1. Refresh the page (Ctrl+R or Cmd+R)
2. Hard refresh: Ctrl+Shift+R
3. Clear browser cache:
   - Settings → Privacy → Clear browsing data
4. Try different browser
5. Ask your admin if still broken

---

### Can't Print Receipt

**Problem:** Click Print, nothing happens or error appears

**Errors & Solutions:**

| Error | Cause | Fix |
|-------|-------|-----|
| "Printer not found" | Thermal printer offline | Check printer power & network |
| "Connection refused" | Wrong printer IP | Verify IP in Settings |
| "PDF failed to generate" | Software error | Restart backend server |
| "Permission denied" | User role issue | Ask owner/manager |

---

### Urdu Text Not Displaying

**Problem:** Urdu text shows as boxes or gibberish

**Solution:**
1. Wait 5-10 seconds (fonts loading)
2. Check internet connection
3. Hard refresh: Ctrl+Shift+R
4. Try different browser
5. Clear browser cache

---

### Report Export Not Working

**Problem:** Click "Export PDF" or "Export CSV", nothing happens

**Solution:**
1. Check internet connection
2. Refresh page
3. Try different browser
4. Check pop-up blocker (allow downloads)
5. Check browser console for errors (F12)

**If file downloads but is corrupted:**
- Try CSV export instead (simpler format)
- Check if file is actually open in another program
- Try again in few seconds

---

### Printer Settings Save But Don't Work

**Problem:** Enter IP/port, save successfully, but receipt still doesn't print

**Solution:**
1. Verify printer is on and connected to network
2. Ping printer IP to test connection:
   - Windows: Open Command Prompt
   - Type: `ping 192.168.1.100` (use your printer IP)
   - Should show "Reply from..." not "Request timed out"
3. Check printer port (default 9100, may be different)
4. Ensure printer supports ESC/POS (thermal printers only)
5. Try setting to "A4" format as test

---

## 🌟 Best Practices

### For Shop Owners

**1. Set Language Once**
- Go to Settings → Appearance → Language
- Choose based on staff preference
- All new staff use this language

**2. Configure Printers Early**
- Get printer IP before opening
- Test with sample receipt
- Save working configuration

**3. Review Reports Daily**
- Check daily audit report
- Look for variances
- Investigate discrepancies same day

**4. Keep Records**
- Export monthly reports as backup
- Store PDFs/CSVs safely
- Reference for accounting

### For Cashiers

**1. Use Language You're Comfortable With**
- Click 🌐 EN button anytime
- Switch between English/Urdu as needed
- Your choice is permanent

**2. Verify Receipts**
- After printing, check receipt format
- Report issues immediately
- Don't ignore printer errors

**3. Flag Problems**
- Printer not working? Tell owner
- Urdu text broken? Report it
- Money mismatch? Investigate

### For Stock Clerks

**1. Language Preference**
- Use 🌐 EN to switch if needed
- Check Products page in your language

**2. Reports Access**
- Inventory reports show current stock
- Use for stock-taking verification

---

## 📋 Quick Reference

| Task | Steps |
|------|-------|
| **Change language** | Click 🌐 EN → Select اردو |
| **Generate audit report** | Audit Reports → Select dates → View Report |
| **Export report as PDF** | View Report → Export PDF |
| **Set printer** | Settings → Printer Options → Enter details → Save |
| **Test printer** | Checkout → Create sale → Print Receipt |
| **Change shop language** | Settings → Appearance → Language → Save |
| **Check daily sales** | Audit Reports → Select Today |

---

## 💡 Tips & Tricks

**Tip 1: Keyboard Shortcuts**
- Hard refresh (clear cache): Ctrl+Shift+R
- Open DevTools (for debugging): F12
- Print page: Ctrl+P

**Tip 2: Export for Analysis**
- Export CSV for Excel analysis
- Export PDF for printing/emailing
- Both formats include all details

**Tip 3: Printer Testing**
- Print test receipt from every printer option
- Verify format, size, and quality
- Save settings once confirmed working

**Tip 4: Multiple Languages**
- Switch between EN/اردو anytime
- Each user can have preference
- No impact on data or transactions

---

## 📞 Getting Help

**For Technical Issues:**
1. Check troubleshooting section above
2. Restart the app (refresh browser)
3. Restart backend server if needed
4. Contact your admin/IT support

**For Feature Questions:**
- Ask your shop owner/manager
- Check this User Guide
- Request training if needed

**For Bug Reports:**
- Take a screenshot
- Note the time and action
- Send to development team

---

## 🚀 Getting Most Value from Features

### Multi-Language Benefits
- **Faster checkout** — Cashiers work in comfortable language
- **Better accuracy** — Reduced confusion with native language UI
- **Staff satisfaction** — Employees appreciate language support

### Reports Benefits  
- **Daily oversight** — Know exactly what happened
- **Trend analysis** — Identify patterns
- **Accountability** — Track cash, discrepancies, voids
- **Compliance** — Keep audit records for tax/legal

### Printer Integration
- **Professional receipts** — Branded with shop info
- **Customer trust** — Formal printed record
- **Flexibility** — Thermal for speed, PDF for backup
- **Cost savings** — Don't reprint due to bad formatting

---

**Questions? Check the troubleshooting section or contact your administrator.**

**Happy POS-ing! 🎉**
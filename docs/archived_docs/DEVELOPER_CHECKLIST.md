# ✅ Developer Checklist — Implementation & Testing

Complete step-by-step checklist for finalizing both features.

---

## 🚀 Phase 0: Immediate Setup (Do This First)

### Backend
- [ ] **Run migrations**
  ```powershell
  cd backend
  .\venv311\Scripts\Activate.ps1
  $env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
  python manage.py migrate
  ```
  **Expect:** No errors. If errors, check CLAUDE.md for settings module help.

- [ ] **Verify media directory created**
  ```powershell
  ls backend/media
  ```
  **Expect:** Directory exists (or will be created on first image upload)

- [ ] **Start backend server**
  ```powershell
  python manage.py runserver
  ```
  **Expect:** "Starting development server at http://127.0.0.1:8000/"

### Frontend
- [ ] **Verify fonts loaded**
  - Open http://localhost:5173 in browser
  - DevTools → Network tab
  - Look for Google Fonts requests (Noto Sans Urdu, Inter)
  - **Expect:** All fonts show as Status 200 (successfully loaded)

- [ ] **Start frontend server**
  ```powershell
  cd frontend
  npm run dev
  ```
  **Expect:** "Local: http://localhost:5173/" (or similar)

- [ ] **Check for TypeScript errors**
  ```powershell
  npm run type-check
  ```
  **Expect:** No errors. If errors, check syntax in components we created.

---

## 🧪 Phase 1: Multi-Language Testing

### Basic Functionality
- [ ] **Sidebar language toggle appears**
  - Navigate to http://localhost:5173
  - Look top-right of sidebar for 🌐 EN button
  - **Expected:** Button visible, says "EN" in small text

- [ ] **Language dropdown works**
  - Click EN button
  - Dropdown appears with "English" and "اردو"
  - **Expected:** Both options visible, clickable

- [ ] **Switching to Urdu works**
  - Click "اردو"
  - UI flips to right-to-left
  - Sidebar nav items change to Urdu
  - **Expected:**
    - Dashboard → ڈیش بورڈ
    - Products → مصنوعات
    - Checkout → چیک آؤٹ
    - Settings → ترتیبات

- [ ] **Font changes to Urdu**
  - DevTools → Elements → `<html>` tag
  - Should have `lang="ur"` and `dir="rtl"`
  - Check computed font-family: should be "Noto Sans Urdu"
  - **Expected:** Text renders in proper Urdu script (not boxes/gibberish)

- [ ] **RTL layout works**
  - After selecting Urdu:
  - Sidebar is on the right
  - Text flows right-to-left
  - Buttons are in correct positions
  - **Expected:** No broken layouts, everything readable

### Persistence & Settings
- [ ] **Language persists after refresh**
  - Select Urdu
  - Refresh page (Ctrl+R)
  - **Expected:** UI still in Urdu (language remembered)

- [ ] **localStorage saves correctly**
  - DevTools → Application → Local Storage → http://localhost:5173
  - Look for "pos-language" key
  - Value should be `{"language":"ur"}`
  - **Expected:** Key exists with correct value

- [ ] **Settings page language dropdown**
  - Go to /settings
  - Scroll down to "Appearance" section
  - Find "Language" setting
  - Should show "اردو" selected (if you're in Urdu mode)
  - **Expected:** Dropdown works, current language selected

- [ ] **Backend setting syncs**
  - Go to Django admin: http://localhost:8000/admin
  - Navigate to Config → Settings
  - Find "language_preference" setting
  - Should show value "ur" (or "en")
  - **Expected:** Setting exists in database

### Translation Coverage
- [ ] **Checkout page partially translated**
  - Go to /checkout
  - Look for "چیک آؤٹ" (Urdu) or "Checkout" (English)
  - Button labels might be in English (we're adding them next)
  - **Expected:** Page title is translated, some buttons still English (Phase 2 task)

- [ ] **Settings page fully translated**
  - Go to /settings in Urdu mode
  - All section headers should be Urdu:
    - "دکان کی معلومات" (Shop Information)
    - "رسید" (Receipt)
    - "تھرمل پرنٹر" (Thermal Printer)
    - "ظہور" (Appearance)
  - **Expected:** All section names in Urdu

- [ ] **Fallback to English works**
  - In code, check `translations.ts`
  - Some keys might only have English (not Urdu)
  - They should fall back to English
  - **Example:** `t("checkoutTitle")` returns English if Urdu missing
  - **Expected:** No blank strings, always shows something

---

## 🖼️ Phase 2: Product Images Testing

### Image Upload
- [ ] **ProductModal shows image upload section**
  - Go to /products
  - Click "+ New Product"
  - Product form opens
  - Top of form: "Product Image" section visible
  - **Expected:** Section shows drag-drop zone with 📤 icon

- [ ] **Drag-drop works**
  - Find an image file on your computer
  - Drag it onto the drop zone
  - **Expected:**
    - Drop zone highlights (changes color)
    - Image preview appears below
    - Remove button visible

- [ ] **File picker works**
  - Click anywhere in drop zone
  - File browser opens (Windows Explorer)
  - Select an image
  - **Expected:** Preview appears instantly

- [ ] **Image validation: file size**
  - Try uploading image > 5MB
  - **Expected:** Alert: "Image must be less than 5MB"

- [ ] **Image validation: file type**
  - Try uploading non-image (PDF, TXT, etc.)
  - **Expected:** Alert: "Please select a valid image (JPEG, PNG, GIF, or WebP)"

- [ ] **Image validation: MIME type**
  - Try renaming BMP to JPG and uploading
  - **Expected:** Should validate actual file type (might accept if MIME correct, reject if wrong)

- [ ] **Remove image works**
  - Upload an image
  - Click "Remove image"
  - **Expected:** Preview disappears, drop zone reappears

### Image Saving
- [ ] **Create product with image**
  - Fill all fields: Name, SKU, Unit, Prices
  - Upload image
  - Click "Create Product"
  - **Expected:**
    - Product saves successfully
    - Modal closes
    - No error messages

- [ ] **Image saved to backend**
  - Check `backend/media/products/` directory
  - Should see image files with random names
  - **Example:** `abc123def456.jpg`
  - **Expected:** File exists with proper image content

- [ ] **Image URL in API**
  - DevTools → Network → Filter to "/products"
  - Load /products page
  - Check API response for a product with image
  - **Expected:** Response has `image` and `image_url` fields:
    ```json
    {
      "id": 1,
      "name": "Blue Tile",
      "image": "products/abc123.jpg",
      "image_url": "http://localhost:8000/media/products/abc123.jpg",
      ...
    }
    ```

### Image Display in List
- [ ] **Thumbnails appear in ProductsPage**
  - Go to /products
  - Products you created with images should show small 32×32px thumbnails
  - Next to each product name
  - **Expected:**
    - Thumbnail visible
    - Proper aspect ratio
    - Lazy loading (check DevTools Network)

- [ ] **Fallback icon for products without images**
  - Find a product without image
  - Should show grey box with 📦 icon
  - **Expected:** Icon renders clearly, not broken

- [ ] **Image loads lazy**
  - DevTools → Network tab
  - Load /products page
  - Scroll down slowly
  - **Expected:** Images load as you scroll (lazy loading)

### Image Editing
- [ ] **Edit product with existing image**
  - Create product with image (if not done already)
  - Click Edit on that product
  - ProductModal opens
  - **Expected:** Image preview shown with "Remove image" button

- [ ] **Replace image**
  - In edit modal, drop new image
  - **Expected:** Old preview replaced with new one

- [ ] **Save image changes**
  - Replace image
  - Click "Save Changes"
  - **Expected:** Modal closes, new image appears in list

---

## 🔍 Phase 3: Integration Testing

### Cross-Feature
- [ ] **Images work in both languages**
  - Create product with image in English mode
  - Switch to Urdu mode
  - Image should still show (not dependent on language)
  - **Expected:** Image appears identically in both languages

- [ ] **Language changes don't affect images**
  - Product list looks same whether English or Urdu
  - Only UI text changes, not images
  - **Expected:** Images are language-agnostic

### API & Database
- [ ] **Migrations applied cleanly**
  - Run `python manage.py showmigrations`
  - Both new migrations should show as applied (✓)
  - **Expected:**
    - `0003_language_setting` ✓
    - `0003_product_image` ✓

- [ ] **Database integrity**
  - Existing products still work
  - Can still create products without images
  - Can edit existing products
  - **Expected:** No "field required" errors for image

- [ ] **API backwards compatible**
  - Products created before image feature still work
  - image_url is null/empty string for old products
  - **Expected:** No API errors for old data

### Performance
- [ ] **No performance regression**
  - Page load time same as before?
  - ProductsPage loads quickly (< 2 seconds)
  - Images don't slow down sorting/filtering
  - **Expected:** UI remains responsive

---

## 🐛 Phase 4: Edge Cases & Error Handling

### Edge Cases
- [ ] **Very small image (1px)**
  - Upload minimal image
  - **Expected:** Saves but looks blurry (accepted)

- [ ] **Exactly 5MB image**
  - Create image exactly 5MB
  - **Expected:** Accepts (not > 5MB)

- [ ] **Upload image, switch language, save**
  - Upload image in English
  - Switch to Urdu
  - Save form
  - **Expected:** Image still saves (language doesn't affect)

- [ ] **Multiple products with same image**
  - Upload same file to 2 products
  - **Expected:** Two separate files in media directory OR same file referenced twice (both acceptable)

- [ ] **Rapid image changes**
  - Upload image
  - Remove
  - Upload different image
  - Remove
  - Upload again
  - Save
  - **Expected:** Final image correct (no glitches)

### Error Handling
- [ ] **Network error during upload**
  - Go offline (disable wifi)
  - Try to create product with image
  - **Expected:** Error message, form doesn't submit

- [ ] **Corrupted image file**
  - Download image, corrupt it (hex editor)
  - Try uploading
  - **Expected:** Either rejects or accepts but shows broken image

- [ ] **Simultaneous edits**
  - Open product edit in 2 browser tabs
  - Change image in tab 1, save
  - Change image in tab 2, save
  - **Expected:** One overwrites the other (acceptable, not ideal)

---

## 🚢 Pre-Production Checklist

### Code Quality
- [ ] **No TypeScript errors**
  ```powershell
  npm run type-check
  ```
  **Expected:** Zero errors

- [ ] **No ESLint warnings**
  ```powershell
  npm run lint
  ```
  **Expected:** Zero errors (warnings acceptable for now)

- [ ] **No console errors**
  - Open DevTools Console
  - Refresh pages
  - **Expected:** No red error messages

- [ ] **No unused imports**
  - Check each file we created/modified
  - Import statements should be used
  - **Example:** `ProductImage` should be imported and used

### Documentation
- [ ] **README updated** (optional but nice)
  - Add line about multi-language support
  - Add line about product images

- [ ] **Code comments added where needed**
  - Complex logic explained
  - Non-obvious functions documented
  - **Example:** Image validation logic should have comment

- [ ] **Types are correct**
  - `Product` interface includes `image_url?: string`
  - `Language` type is `"en" | "ur"`
  - All serializer types match API response

### Browser Compatibility
- [ ] **Works in Chrome** (primary)
  - Run through all tests
  - **Expected:** Everything works

- [ ] **Works in Firefox** (secondary)
  - Quick smoke test
  - Images load, language switches
  - **Expected:** No major issues

- [ ] **Works on Windows & Mac** (if available)
  - Test on both platforms
  - **Expected:** Consistent behavior

---

## 📋 Git Commit Checklist

Before committing:
- [ ] All files created/modified are listed
- [ ] No accidental console.log() left in code
- [ ] No debug code committed
- [ ] All imports are clean (no unused)
- [ ] TypeScript types are correct
- [ ] Database migrations are numbered correctly

Suggested commits:
```bash
# Language feature
git add frontend/src/store/languageStore.ts
git add frontend/src/lib/translations.ts
git add frontend/src/hooks/useTranslation.ts
git add frontend/src/components/LanguageToggle.tsx
git add frontend/src/layouts/ProtectedLayout.tsx
git add frontend/src/pages/SettingsPage.tsx
git add frontend/index.html
git add frontend/src/index.css
git add backend/apps/config/migrations/0003_language_setting.py
git commit -m "feat: add multi-language support (EN/اردو) with RTL layout"

# Product images feature
git add frontend/src/components/ProductImage.tsx
git add frontend/src/components/catalog/ProductModal.tsx
git add frontend/src/pages/ProductsPage.tsx
git add frontend/src/types/catalog.ts
git add backend/apps/catalog/models.py
git add backend/apps/catalog/serializers.py
git add backend/apps/catalog/migrations/0003_product_image.py
git commit -m "feat: add product image upload with drag-drop UI and list thumbnails"
```

---

## 🎯 Success Criteria (All Must Pass)

### Feature Completeness
- ✅ Language toggle visible and functional
- ✅ Language persists (localStorage)
- ✅ UI translates to Urdu with RTL layout
- ✅ Settings page has language dropdown
- ✅ Image upload form appears in ProductModal
- ✅ Image validation works
- ✅ Images display in ProductsPage list
- ✅ Images save to backend/media/products/

### User Experience
- ✅ No broken UI elements
- ✅ No confusing error messages
- ✅ Language toggle is obvious (🌐 button)
- ✅ Image upload is intuitive (drag-drop)
- ✅ Fallback icons appear for missing images
- ✅ RTL layout feels natural

### Technical Quality
- ✅ No TypeScript errors
- ✅ Database migrations run cleanly
- ✅ API responses include image_url
- ✅ Backwards compatible (old products still work)
- ✅ Performance acceptable (< 2 second page load)

### Testing Coverage
- ✅ Both features tested end-to-end
- ✅ Edge cases handled
- ✅ Error messages clear
- ✅ Cross-browser compatible (at least Chrome + Firefox)

---

## 🎉 Final Steps

When all checkboxes are ✅:

1. **Clean up any leftover comments/debug code**
2. **Do a final git status check**
3. **Run migrations one more time**
4. **Take screenshots for documentation**
5. **Create PR/commit with clear message**
6. **Share FEATURE_SUMMARY.md with team**
7. **Share USER_GUIDE.md with shop owner**

---

**You're done when all checkboxes are checked! 🎊**
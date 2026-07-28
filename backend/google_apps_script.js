/**
 * RZWire — Google Apps Script template
 *
 * SETUP INSTRUCTIONS:
 * 1. Go to https://script.google.com → New Project
 * 2. Paste this entire file, replacing the default Code.gs content
 * 3. Click Run → "setup" (first time only) — this creates the sheet and 4 tabs
 * 4. Click Deploy → New Deployment → Web App
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 5. Copy the Web App URL and paste it in backend/.env as GOOGLE_APPS_SCRIPT_URL
 */

// ── One-time setup: creates the spreadsheet tabs ──────────────────────────────
function setup() {
  const ss   = SpreadsheetApp.getActiveSpreadsheet();
  const tabs = ['MGC Coin', 'Ranking Platform', 'Oasis Coin', 'Jewelry Coin'];
  const headers = [
    'ID', 'Timestamp', 'Title', 'Source', 'Source URL',
    'Media Brand', 'Platform', 'Generated Copy', 'Hashtags',
    'Sentiment', 'Fit Score', 'Impact Score', 'Virality Score',
    'Image Status', 'Image URL', 'Approval Status',
    'Scheduled Date', 'Scheduled Time', 'Notes',
  ];

  // Remove default "Sheet1" if empty
  const defaultSheet = ss.getSheetByName('Sheet1');
  if (defaultSheet && ss.getSheets().length > 1) ss.deleteSheet(defaultSheet);

  tabs.forEach(name => {
    let sheet = ss.getSheetByName(name);
    if (!sheet) sheet = ss.insertSheet(name);
    if (sheet.getLastRow() === 0) {
      const range = sheet.getRange(1, 1, 1, headers.length);
      range.setValues([headers]);
      range.setFontWeight('bold');
      range.setBackground('#1a1a2e');
      range.setFontColor('#ffffff');
      sheet.setFrozenRows(1);
    }
  });

  Logger.log('Setup complete — 4 tabs created.');
}

// ── Main entry point ───────────────────────────────────────────────────────────
function doPost(e) {
  try {
    const data   = JSON.parse(e.postData.contents);
    const action = data.action;

    if (action === 'approve')      return respond(handleApprove(data));
    if (action === 'schedule')     return respond(handleSchedule(data));
    if (action === 'update')       return respond(handleUpdate(data));
    if (action === 'uploadImage')  return respond(handleImageUpload(data));

    return respond({ success: false, error: 'Unknown action: ' + action });
  } catch (err) {
    return respond({ success: false, error: err.message });
  }
}

// ── Approve: append or update row in the media brand tab ──────────────────────
function handleApprove(data) {
  const sheet = getSheet(data.mediaBrand);

  const row = [
    data.id || generateId(),
    new Date().toISOString(),
    data.title        || '',
    data.source       || '',
    data.sourceUrl    || '',
    data.mediaBrand   || '',
    data.platform     || '',
    data.copy         || '',
    Array.isArray(data.hashtags) ? data.hashtags.join(' ') : (data.hashtags || ''),
    data.sentiment    || '',
    data.fitScore     || '',
    data.impactScore  || '',
    data.viralityScore|| '',
    data.imageStatus  || 'No Image',
    data.imageUrl     || '',
    'Approved',
    '', '', '',
  ];

  const existingRow = findRowById(sheet, data.id);
  if (existingRow > 0) {
    sheet.getRange(existingRow, 1, 1, row.length).setValues([row]);
    return { success: true, action: 'updated', row: existingRow };
  }
  sheet.appendRow(row);
  return { success: true, action: 'appended', row: sheet.getLastRow() };
}

// ── Schedule: set scheduled date/time on existing or new row ─────────────────
function handleSchedule(data) {
  const sheet = getSheet(data.mediaBrand);
  const existingRow = findRowById(sheet, data.id);

  if (existingRow > 0) {
    sheet.getRange(existingRow, 16).setValue('Scheduled');
    sheet.getRange(existingRow, 17).setValue(data.scheduledDate || '');
    sheet.getRange(existingRow, 18).setValue(data.scheduledTime || '');
    return { success: true, action: 'updated' };
  }

  // Create new row if not yet in sheet
  const row = [
    data.id || generateId(),
    new Date().toISOString(),
    data.title || '', data.source || '', data.sourceUrl || '',
    data.mediaBrand || '', data.platform || '', data.copy || '',
    Array.isArray(data.hashtags) ? data.hashtags.join(' ') : (data.hashtags || ''),
    data.sentiment || '', data.fitScore || '', data.impactScore || '',
    data.viralityScore || '', 'No Image', '', 'Scheduled',
    data.scheduledDate || '', data.scheduledTime || '', '',
  ];
  sheet.appendRow(row);
  return { success: true, action: 'scheduled' };
}

// ── Update: patch image URL / status on existing row ─────────────────────────
function handleUpdate(data) {
  const sheet = getSheet(data.mediaBrand);
  const existingRow = findRowById(sheet, data.id);
  if (existingRow < 0) return { success: false, error: 'Row not found for id: ' + data.id };

  if (data.imageUrl)    sheet.getRange(existingRow, 15).setValue(data.imageUrl);
  if (data.imageStatus) sheet.getRange(existingRow, 14).setValue(data.imageStatus);
  if (data.approvalStatus) sheet.getRange(existingRow, 16).setValue(data.approvalStatus);
  return { success: true };
}

// ── Image Upload: save base64 image to Drive ─────────────────────────────────
function handleImageUpload(data) {
  const folderName = 'RZWire Images';
  const folders = DriveApp.getFoldersByName(folderName);
  const folder  = folders.hasNext() ? folders.next() : DriveApp.createFolder(folderName);

  let blob;
  if (data.imageB64) {
    // Frontend sent base64 (from DALL-E b64_json response)
    const bytes = Utilities.base64Decode(data.imageB64);
    blob = Utilities.newBlob(bytes, 'image/png');
  } else if (data.imageUrl) {
    // Fallback: fetch from URL
    const response = UrlFetchApp.fetch(data.imageUrl, { muteHttpExceptions: true });
    if (response.getResponseCode() !== 200) return { success: false, error: 'Failed to fetch image URL' };
    blob = response.getBlob();
  } else {
    return { success: false, error: 'No image data provided' };
  }

  const filename = `${(data.mediaBrand || 'post').replace(/\s+/g,'_')}_${data.platform || 'post'}_${Date.now()}.png`;
  blob.setName(filename);

  const file = folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  const driveUrl = `https://drive.google.com/uc?export=view&id=${file.getId()}`;
  return { success: true, driveUrl, fileId: file.getId() };
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function getSheet(name) {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(name);
  if (!sheet) throw new Error(`Tab not found: "${name}". Run setup() first.`);
  return sheet;
}

function findRowById(sheet, id) {
  if (!id) return -1;
  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (String(values[i][0]) === String(id)) return i + 1;
  }
  return -1;
}

function generateId() {
  return 'cr_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);
}

function respond(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

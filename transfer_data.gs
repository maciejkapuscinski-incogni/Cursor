/**
 * Google Apps Script to transfer data from cell A1 to A2
 * This script copies the value from cell A1 and pastes it to cell A2
 */

function transferDataFromA1ToA2() {
  // Get the active spreadsheet
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  // Get the active sheet (or you can specify a specific sheet)
  var sheet = spreadsheet.getActiveSheet();
  
  // Get the value from cell A1
  var valueFromA1 = sheet.getRange('A1').getValue();
  
  // Set the value to cell A2
  sheet.getRange('A2').setValue(valueFromA1);
  
  // Optional: Log the transfer for debugging
  console.log('Data transferred from A1 to A2: ' + valueFromA1);
  
  // Optional: Show a message to the user
  SpreadsheetApp.getUi().alert('Data successfully transferred from A1 to A2!');
}

/**
 * Alternative function that preserves formatting
 * This version copies both value and formatting from A1 to A2
 */
function transferDataWithFormatting() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = spreadsheet.getActiveSheet();
  
  // Get the range A1
  var sourceRange = sheet.getRange('A1');
  
  // Copy the range (value and formatting)
  sourceRange.copyTo(sheet.getRange('A2'));
  
  console.log('Data and formatting transferred from A1 to A2');
  SpreadsheetApp.getUi().alert('Data and formatting successfully transferred from A1 to A2!');
}

/**
 * Function to transfer data and clear A1
 * This moves the data from A1 to A2 and clears A1
 */
function moveDataFromA1ToA2() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = spreadsheet.getActiveSheet();
  
  // Get the value from A1
  var valueFromA1 = sheet.getRange('A1').getValue();
  
  // Set the value to A2
  sheet.getRange('A2').setValue(valueFromA1);
  
  // Clear A1
  sheet.getRange('A1').clear();
  
  console.log('Data moved from A1 to A2 and A1 cleared');
  SpreadsheetApp.getUi().alert('Data moved from A1 to A2 and A1 cleared!');
}
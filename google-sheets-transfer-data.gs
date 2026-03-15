/**
 * Google Apps Script to transfer data from cell A1 to A2
 * This script copies the value from cell A1 and pastes it to cell A2
 */

function transferDataFromA1ToA2() {
  // Get the active spreadsheet
  const sheet = SpreadsheetApp.getActiveSheet();
  
  // Get the value from cell A1
  const valueFromA1 = sheet.getRange('A1').getValue();
  
  // Set the value to cell A2
  sheet.getRange('A2').setValue(valueFromA1);
  
  // Optional: Log the transfer for debugging
  console.log(`Data transferred from A1 to A2: ${valueFromA1}`);
}

/**
 * Alternative function that preserves formatting
 * This version copies both value and formatting from A1 to A2
 */
function transferDataWithFormatting() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  // Get the range A1
  const sourceRange = sheet.getRange('A1');
  
  // Copy the range (value and formatting)
  sourceRange.copyTo(sheet.getRange('A2'));
  
  console.log('Data and formatting transferred from A1 to A2');
}

/**
 * Function to clear A1 after transferring to A2
 * Use this if you want to move the data instead of copying it
 */
function moveDataFromA1ToA2() {
  const sheet = SpreadsheetApp.getActiveSheet();
  
  // Get the value from A1
  const valueFromA1 = sheet.getRange('A1').getValue();
  
  // Set the value to A2
  sheet.getRange('A2').setValue(valueFromA1);
  
  // Clear A1
  sheet.getRange('A1').clear();
  
  console.log(`Data moved from A1 to A2: ${valueFromA1}`);
}

/**
 * Function to transfer data with error handling
 * This version includes proper error handling
 */
function transferDataWithErrorHandling() {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();
    
    // Check if A1 has any data
    const valueFromA1 = sheet.getRange('A1').getValue();
    
    if (valueFromA1 === '') {
      console.log('Cell A1 is empty, nothing to transfer');
      return;
    }
    
    // Transfer the data
    sheet.getRange('A2').setValue(valueFromA1);
    
    console.log(`Successfully transferred data from A1 to A2: ${valueFromA1}`);
    
  } catch (error) {
    console.error('Error occurred while transferring data:', error);
  }
}
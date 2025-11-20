/**
 * Case-specific conversion-rate inputs that remain available to the entire
 * Apps Script project. Each case exposes the five requested values.
 */
const CASE_DATA = {
  worst: {
    label: 'Worst case',
    metrics: {
      cr_paid: 0.8,
      cr_paid_sitelink: 0.6,
      cr_seo_lp: 0.5,
      cr_seo_blog: 0.4,
      cr_affiliate: 0.3,
      scans_affiliate: 10,
      cr_direct: 0.7,
      AOV: 45,
    },
  },
  realistic: {
    label: 'Realistic case',
    metrics: {
      cr_paid: 1.5,
      cr_paid_sitelink: 1.4,
      cr_seo_lp: 1.2,
      cr_seo_blog: 1.0,
      cr_affiliate: 0.9,
      scans_affiliate: 30,
      cr_direct: 1.2,
      AOV: 60,
    },
  },
  best: {
    label: 'Best case',
    metrics: {
      cr_paid: 2.5,
      cr_paid_sitelink: 2.2,
      cr_seo_lp: 2.0,
      cr_seo_blog: 1.8,
      cr_affiliate: 1.6,
      scans_affiliate: 60,
      cr_direct: 2.1,
      AOV: 95,
    },
  },
};

const SLIDER_PROPERTY_KEY = 'current_slider_points';
const CASE_PROPERTY_KEY = 'current_case_key';
const DEFAULT_SLIDER_VALUE = 50;
const DEFAULT_CASE_KEY = 'worst';
const STATE_SHEET_NAME = '_ExposureState';
const CALCULATION_SHEET_NAME = 'Calculation';
const CALCULATION_SCENARIO_CELL = 'F9';

/**
 * Adds a simple custom menu entry to launch the sidebar.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Exposure Calculator')
    .addItem('Open Controls', 'showSidebar')
    .addToUi();
  showSidebar();
}

/**
 * Renders the sidebar UI defined in sidebar.html.
 */
function showSidebar() {
  const sidebar = HtmlService.createHtmlOutputFromFile('sidebar')
    .setTitle('Exposure Controls')
    .setWidth(320);
  SpreadsheetApp.getUi().showSidebar(sidebar);
}

/**
 * Returns the available case data plus the user's latest selections.
 */
function getSidebarData() {
  const props = PropertiesService.getScriptProperties();
  const sliderValue = Number(
    props.getProperty(SLIDER_PROPERTY_KEY) || DEFAULT_SLIDER_VALUE
  );
  const caseKey = props.getProperty(CASE_PROPERTY_KEY) || DEFAULT_CASE_KEY;
  return {
    sliderValue,
    caseKey,
    cases: CASE_DATA,
  };
}

/**
 * Persists the slider value for downstream use in other functions.
 * @param {number} value
 */
function saveSliderValue(value) {
  const sanitized = Math.max(1, Math.min(100, Number(value) || DEFAULT_SLIDER_VALUE));
  PropertiesService.getScriptProperties().setProperty(
    SLIDER_PROPERTY_KEY,
    String(sanitized)
  );
  updateStateSheet_();
  return sanitized;
}

/**
 * Persists the chosen case key and exposes its metrics.
 * @param {string} caseKey
 */
function saveCaseSelection(caseKey) {
  if (!CASE_DATA[caseKey]) {
    throw new Error('Unknown case selection');
  }
  PropertiesService.getScriptProperties().setProperty(
    CASE_PROPERTY_KEY,
    caseKey
  );
  updateStateSheet_();
  return CASE_DATA[caseKey];
}

/**
 * Helper that other project functions can call to fetch the latest inputs.
 */
function getCurrentExposureInputs() {
  const props = PropertiesService.getScriptProperties();
  const sliderValue = Number(
    props.getProperty(SLIDER_PROPERTY_KEY) || DEFAULT_SLIDER_VALUE
  );
  const caseKey = props.getProperty(CASE_PROPERTY_KEY) || DEFAULT_CASE_KEY;
  return {
    sliderValue,
    caseKey,
    metrics: CASE_DATA[caseKey].metrics,
  };
}

function updateStateSheet_() {
  const sheet = getOrCreateStateSheet_();
  const state = getCurrentExposureInputs();
  const rows = [
    ['Field', 'Value'],
    ['trigger', Date.now()],
    ['sliderValue', state.sliderValue],
    ['caseKey', state.caseKey],
    ['cr_paid', state.metrics.cr_paid],
    ['cr_paid_sitelink', state.metrics.cr_paid_sitelink],
    ['cr_seo_lp', state.metrics.cr_seo_lp],
    ['cr_seo_blog', state.metrics.cr_seo_blog],
    ['cr_affiliate', state.metrics.cr_affiliate],
    ['scans_affiliate', state.metrics.scans_affiliate],
    ['cr_direct', state.metrics.cr_direct],
    ['AOV', state.metrics.AOV],
  ];
  sheet.clearContents();
  sheet.getRange(1, 1, rows.length, 2).setValues(rows);
  sheet.hideSheet();
  updateCalculationScenarioLabel_(state.caseKey);
  SpreadsheetApp.flush();
}

function getOrCreateStateSheet_() {
  const ss = SpreadsheetApp.getActive();
  let sheet = ss.getSheetByName(STATE_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(STATE_SHEET_NAME);
    sheet.hideSheet();
  }
  return sheet;
}

function updateCalculationScenarioLabel_(caseKey) {
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(CALCULATION_SHEET_NAME);
  if (!sheet) {
    return;
  }
  const label = CASE_DATA[caseKey]?.label || '';
  sheet.getRange(CALCULATION_SCENARIO_CELL).setValue(label);
}



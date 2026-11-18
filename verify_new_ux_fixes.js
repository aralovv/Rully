const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://127.0.0.1:8080/';
const SCREENSHOT_DIR = path.join(__dirname, 'audit_screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function verifyNewUXFixes() {
  console.log('--- STARTING VERIFICATION: Language Pill, Icon Size, Slider, Scenarios ---');
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });
  page.on('dialog', async dialog => {
    console.log('Dialog opened:', dialog.message());
    await dialog.accept();
  });

  const results = {
    headerLangPillDefaultUZ: false,
    headerLangPillChanges: false,
    aralashSavollarTextClean: false,
    telegramSliderWorks: false,
    correctIconSizingSmall: false,
    scenariosStepNavigationWorks: false,
    scenariosAllThreeReachable: false,
    scenariosCompletionWorks: false
  };

  try {
    console.log('1. Navigating to', BASE_URL);
    await page.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 800));

    // 1. Header Language Pill check
    const initialLang = await page.$eval('#header-lang-label', el => el.textContent.trim());
    console.log('Header lang label initial:', initialLang);
    results.headerLangPillDefaultUZ = (initialLang === 'UZ');

    // Go to Profil to test language switching
    await page.click('#nav-profile');
    await new Promise(r => setTimeout(r, 600));

    // Click Cyrillic
    await page.click('.lang-selector-tile[data-lang="uz_cyrl"]');
    await new Promise(r => setTimeout(r, 500));
    const cyrlLang = await page.$eval('#header-lang-label', el => el.textContent.trim());
    console.log('Header lang label on Cyrillic:', cyrlLang);

    // Click Russian
    await page.click('.lang-selector-tile[data-lang="ru"]');
    await new Promise(r => setTimeout(r, 500));
    const ruLang = await page.$eval('#header-lang-label', el => el.textContent.trim());
    console.log('Header lang label on Russian:', ruLang);

    // Click back to Latin
    await page.click('.lang-selector-tile[data-lang="uz_latn"]');
    await new Promise(r => setTimeout(r, 500));
    const finalLatin = await page.$eval('#header-lang-label', el => el.textContent.trim());
    console.log('Header lang label restored Latin:', finalLatin);

    results.headerLangPillChanges = (cyrlLang === 'УЗ' && ruLang === 'РУ' && finalLatin === 'UZ');

    // 2. Test Nazariya and Aralash Savollar text
    console.log('2. Testing Nazariya and Aralash Savollar card...');
    await page.click('#nav-tests');
    await new Promise(r => setTimeout(r, 600));

    const cardTitle = await page.$eval('.custom-quiz-title', el => el.textContent.trim());
    console.log('Aralash Savollar card title:', cardTitle);
    results.aralashSavollarTextClean = (cardTitle === 'Aralash savollar');

    // 3. Test Telegram Range Slider in Settings
    console.log('3. Testing Telegram Range Slider in Settings modal...');
    await page.click('#btn-open-custom-quiz-settings');
    await new Promise(r => setTimeout(r, 500));

    const sliderInitialVal = await page.$eval('#slider-time-val-badge', el => el.textContent.trim());
    console.log('Initial slider time badge:', sliderInitialVal);

    // Click Cheksiz tick label (index 6)
    await page.click('#slider-tick-labels span[data-idx="6"]');
    await new Promise(r => setTimeout(r, 300));
    const sliderCheksizVal = await page.$eval('#slider-time-val-badge', el => el.textContent.trim());
    console.log('Slider time badge on Cheksiz:', sliderCheksizVal);

    // Click 10d tick label (index 1)
    await page.click('#slider-tick-labels span[data-idx="1"]');
    await new Promise(r => setTimeout(r, 300));
    const slider10dVal = await page.$eval('#slider-time-val-badge', el => el.textContent.trim());
    console.log('Slider time badge on 10d:', slider10dVal);

    results.telegramSliderWorks = (sliderCheksizVal.includes('Cheksiz') && slider10dVal.includes('10 daqiqa'));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'verify_telegram_slider.png') });

    // Close settings modal
    await page.click('#btn-close-settings-modal');
    await new Promise(r => setTimeout(r, 400));

    // 4. Test Quiz HUD and Feedback icon size
    console.log('4. Testing Quiz HUD feedback icon sizing...');
    // Click Hero Start Exam button
    await page.click('#nav-home');
    await new Promise(r => setTimeout(r, 500));
    await page.click('#btn-hero-start-exam');
    await new Promise(r => setTimeout(r, 1000));

    // Click first option
    await page.evaluate(() => {
      const card = document.querySelector('#quiz-options-list .tactical-option-card');
      if (card) card.click();
    });
    await new Promise(r => setTimeout(r, 800));

    // Measure icon in statutory-header
    const iconDimensions = await page.evaluate(() => {
      const svg = document.querySelector('#quiz-feedback-box .statutory-header svg');
      if (!svg) return null;
      const rect = svg.getBoundingClientRect();
      return { width: rect.width, height: rect.height };
    });
    console.log('Feedback header icon dimensions:', iconDimensions);
    if (iconDimensions && iconDimensions.width <= 20 && iconDimensions.height <= 20) {
      results.correctIconSizingSmall = true;
    }
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'verify_correct_icon_size.png') });

    // Close quiz overlay
    await page.click('#btn-close-quiz');
    await new Promise(r => setTimeout(r, 400));

    // 5. Test Vaziyatlar (Scenarios) in Avtodrom
    console.log('5. Testing Vaziyatlar (Scenarios) navigation & interaction...');
    await page.click('#nav-amaliy');
    await new Promise(r => setTimeout(r, 500));

    // Click Vaziyatlar sub-tab
    await page.click('.practical-sub-tab[data-section="scenarios"]');
    await new Promise(r => setTimeout(r, 600));

    const s1Title = await page.$eval('#scenario-title', el => el.textContent.trim());
    console.log('Scenario 1 title:', s1Title);

    // Answer scenario 1
    await page.evaluate(() => {
      const opt = document.querySelector('#scenario-options .tactical-option-card');
      if (opt) opt.click();
    });
    await new Promise(r => setTimeout(r, 800));

    const s1FeedbackVisible = await page.$eval('#scenario-feedback', el => el.style.display !== 'none');
    console.log('Scenario 1 feedback visible:', s1FeedbackVisible);

    // Check feedback icon size in scenario
    const scenIconDims = await page.evaluate(() => {
      const svg = document.querySelector('#scenario-feedback .statutory-header svg');
      return svg ? { width: svg.getBoundingClientRect().width, height: svg.getBoundingClientRect().height } : null;
    });
    console.log('Scenario feedback icon dimensions:', scenIconDims);

    // Advance to Scenario 2
    console.log('Advancing to Scenario 2...');
    await page.click('#btn-scenario-next');
    await new Promise(r => setTimeout(r, 500));

    const s2Title = await page.$eval('#scenario-title', el => el.textContent.trim());
    console.log('Scenario 2 title:', s2Title);

    // Check that feedback was reset and is not leaking
    const s2FeedbackHidden = await page.$eval('#scenario-feedback', el => el.style.display === 'none');
    console.log('Scenario 2 feedback initially hidden:', s2FeedbackHidden);

    // Answer scenario 2
    await page.evaluate(() => {
      const opt = document.querySelector('#scenario-options .tactical-option-card');
      if (opt) opt.click();
    });
    await new Promise(r => setTimeout(r, 800));

    // Advance to Scenario 3
    console.log('Advancing to Scenario 3...');
    await page.click('#btn-scenario-next');
    await new Promise(r => setTimeout(r, 500));

    const s3Title = await page.$eval('#scenario-title', el => el.textContent.trim());
    console.log('Scenario 3 title:', s3Title);

    results.scenariosStepNavigationWorks = (s1Title !== s2Title && s2Title !== s3Title);
    results.scenariosAllThreeReachable = (s3Title.length > 0);

    // Answer scenario 3
    await page.evaluate(() => {
      const opt = document.querySelector('#scenario-options .tactical-option-card');
      if (opt) opt.click();
    });
    await new Promise(r => setTimeout(r, 800));

    // Finish scenarios
    console.log('Finishing scenarios (summary check)...');
    await page.click('#btn-scenario-next');
    await new Promise(r => setTimeout(r, 600));

    const summaryVisible = await page.$eval('#scenario-summary-card', el => el.style.display !== 'none');
    const scoreVal = await page.$eval('#scenario-summary-score', el => el.textContent.trim());
    console.log('Summary card visible:', summaryVisible, '| Score:', scoreVal);
    results.scenariosCompletionWorks = summaryVisible;

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'verify_scenarios_summary.png') });

    console.log('\n--- VERIFICATION TEST COMPLETE ---');
    console.log(JSON.stringify(results, null, 2));

  } catch (err) {
    console.error('Verification error:', err);
  } finally {
    await browser.close();
  }
}

verifyNewUXFixes();

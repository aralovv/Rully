const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://127.0.0.1:8080/';
const SCREENSHOT_DIR = path.join(__dirname, 'audit_screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runVerification() {
  console.log('--- STARTING VERIFICATION: Custom Quiz, Avtodrom Sub-tabs, Checklist Cleanliness ---');
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });

  const results = {
    checklistClean: false,
    checklistText: '',
    avtodromSubtabsSwitch: false,
    settingsModalOpens: false,
    customQuizOptionsWork: false,
    customQuizSessionStarts: false,
    timerUnlimitedInfinite: false,
    optionsRenderCorrectly: false
  };

  try {
    console.log('1. Navigating to', BASE_URL);
    await page.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 15000 });

    // Wait for telemetry to load
    await new Promise(r => setTimeout(r, 1000));

    // 2. Check Avtodrom and Checklist
    console.log('2. Testing Avtodrom view & sub-tabs...');
    await page.click('#nav-amaliy');
    await new Promise(r => setTimeout(r, 800));

    // Test Checklist tab
    const checklistTabBtn = await page.$('.practical-sub-tab[data-section="checklist"]');
    if (checklistTabBtn) {
      await checklistTabBtn.click();
      await new Promise(r => setTimeout(r, 600));

      const isChecklistActive = await page.$eval('.practical-sub-tab[data-section="checklist"]', el => el.classList.contains('active'));
      const activeTabStyle = await page.$eval('.practical-sub-tab[data-section="checklist"]', el => {
        const cs = window.getComputedStyle(el);
        return { background: cs.backgroundImage || cs.backgroundColor, color: cs.color, border: cs.borderColor };
      });
      console.log('Checklist tab active:', isChecklistActive, 'style:', activeTabStyle);

      const chkText = await page.$eval('#checklist-pct-text', el => el.textContent.trim());
      console.log('Checklist percentage text:', chkText);
      results.checklistText = chkText;

      if (!chkText.includes('{pct}') && !chkText.includes('{done}') && !chkText.includes('{total}') && chkText.includes('%')) {
        results.checklistClean = true;
      }
    }

    // Test Sim tab
    const simTabBtn = await page.$('.practical-sub-tab[data-section="sim"]');
    if (simTabBtn) {
      await simTabBtn.click();
      await new Promise(r => setTimeout(r, 500));
      const isSimActive = await page.$eval('.practical-sub-tab[data-section="sim"]', el => el.classList.contains('active'));
      console.log('Sim tab active after click:', isSimActive);
      results.avtodromSubtabsSwitch = isSimActive;
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'verify_avtodrom_subtabs.png') });

    // 3. Test Nazariya & Custom Quiz
    console.log('3. Testing Nazariya view & Custom Quiz Settings...');
    await page.click('#nav-tests');
    await new Promise(r => setTimeout(r, 800));

    const customCardVisible = await page.$eval('.custom-quiz-launch-card', el => {
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });
    console.log('Custom Quiz Launch Card visible:', customCardVisible);

    // Click to open settings modal
    await page.click('#btn-open-custom-quiz-settings');
    await new Promise(r => setTimeout(r, 500));

    const isModalActive = await page.$eval('#custom-quiz-settings-modal', el => el.classList.contains('active'));
    console.log('Custom Quiz Settings modal active:', isModalActive);
    results.settingsModalOpens = isModalActive;

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'verify_custom_quiz_settings_modal.png') });

    // Select 10 questions chip
    const chip10 = await page.$('#chips-q-count button[data-val="10"]');
    if (chip10) {
      await chip10.click();
      await new Promise(r => setTimeout(r, 200));
    }

    // Select Cheksiz (unlimited) time chip
    const chipCheksiz = await page.$('#chips-time-limit button[data-val="0"]');
    if (chipCheksiz) {
      await chipCheksiz.click();
      await new Promise(r => setTimeout(r, 200));
    }

    const is10Active = await page.$eval('#chips-q-count button[data-val="10"]', el => el.classList.contains('active'));
    const isCheksizActive = await page.$eval('#chips-time-limit button[data-val="0"]', el => el.classList.contains('active'));
    console.log('Chip 10 active:', is10Active, '| Chip Cheksiz active:', isCheksizActive);
    results.customQuizOptionsWork = is10Active && isCheksizActive;

    // Click Start Quiz
    console.log('4. Starting Custom Quiz...');
    await page.click('#btn-start-custom-quiz');
    await new Promise(r => setTimeout(r, 1200));

    const isQuizActive = await page.$eval('#quiz-overlay', el => el.classList.contains('active'));
    const counterText = await page.$eval('#quiz-counter-text', el => el.textContent.trim());
    const timerText = await page.$eval('#quiz-timer-val', el => el.textContent.trim());

    console.log('Quiz overlay active:', isQuizActive);
    console.log('Counter text:', counterText);
    console.log('Timer text:', timerText);

    results.customQuizSessionStarts = isQuizActive && counterText === '01 / 10';
    results.timerUnlimitedInfinite = (timerText === '∞');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'verify_custom_quiz_active.png') });

    // Answer a question
    console.log('5. Submitting answer on custom quiz...');
    await page.evaluate(() => {
      const card = document.querySelector('#quiz-options-list .tactical-option-card');
      if (card) card.click();
    });
    await new Promise(r => setTimeout(r, 1000));

    const hasAnswerClass = await page.evaluate(() => {
      const card = document.querySelector('#quiz-options-list .tactical-option-card.correct, #quiz-options-list .tactical-option-card.wrong');
      return !!card;
    });
    console.log('Selected option evaluated with answer class:', hasAnswerClass);
    results.optionsRenderCorrectly = hasAnswerClass;

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'verify_custom_quiz_answered.png') });

    console.log('\n--- VERIFICATION AUDIT COMPLETE ---');
    console.log(JSON.stringify(results, null, 2));

  } catch (err) {
    console.error('Verification error:', err);
  } finally {
    await browser.close();
  }
}

runVerification();

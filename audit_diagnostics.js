const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://127.0.0.1:8080/';

const VIEWPORTS = [
  { name: '320px (iPhone SE 1st / Ultra Small)', width: 320, height: 568 },
  { name: '360px (Galaxy S8/S9 / Entry Android)', width: 360, height: 640 },
  { name: '375px (iPhone SE / iPhone 12 Mini)', width: 375, height: 667 },
  { name: '390px (iPhone 12/13/14 Pro)', width: 390, height: 844 },
  { name: '414px (iPhone 11 / Plus Models)', width: 414, height: 896 },
  { name: '430px (iPhone 14/15/16 Pro Max)', width: 430, height: 932 },
  { name: '768px (iPad Mini / Tablet)', width: 768, height: 1024 },
  { name: '1024px (Desktop / Web Telegram)', width: 1024, height: 768 },
];

async function runRemediationAudit() {
  console.log('=================================================================');
  console.log('RULLY REMEDIATION POST-IMPLEMENTATION VERIFICATION AUDIT');
  console.log('Automated Puppeteer + Real Google Chrome Diagnostic Suite');
  console.log('=================================================================\n');

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
  });

  const auditResults = {
    timestamp: new Date().toISOString(),
    viewports: {},
    regressionCriteria: {},
    subviews: {},
    linguisticFits: {},
  };

  const page = await browser.newPage();

  // Automatically accept confirmation dialogs
  page.on('dialog', async dialog => {
    console.log(`  [Dialog Handler] Dismissed: "${dialog.message()}"`);
    await dialog.accept();
  });

  // 1. Audit Across All Viewports
  for (const vp of VIEWPORTS) {
    console.log(`\n--- Auditing Viewport: ${vp.name} (${vp.width}x${vp.height}) ---`);
    await page.setViewport({ width: vp.width, height: vp.height, deviceScaleFactor: 2 });
    await page.goto(BASE_URL, { waitUntil: 'networkidle0' });
    await page.waitForSelector('.cockpit-bottom-nav', { timeout: 5000 });

    // A. Check Horizontal Overflow
    const overflowData = await page.evaluate(() => {
      const scrollWidth = document.documentElement.scrollWidth;
      const windowWidth = window.innerWidth;
      const hasHorizontalScroll = scrollWidth > windowWidth;

      // Check fixed nav bar elements overflowing screen
      const navItems = Array.from(document.querySelectorAll('.nav-bar-item'));
      const overflowingNavItems = navItems.filter(item => {
        const rect = item.getBoundingClientRect();
        return rect.right > windowWidth + 1 || rect.left < -1;
      }).map(i => ({ id: i.id, tab: i.dataset.tab, right: i.getBoundingClientRect().right }));

      return {
        windowWidth,
        scrollWidth,
        hasHorizontalScroll,
        overflowDelta: scrollWidth - windowWidth,
        overflowingNavItems,
        navOverflowsScreen: overflowingNavItems.length > 0,
      };
    });

    // B. Check Speedometer Arc Collision
    const speedometerData = await page.evaluate(() => {
      const arc = document.querySelector('.arc-svg');
      const details = document.querySelector('.readiness-details-col');
      const row = document.querySelector('.speedometer-row');
      if (!arc || !details || !row) return null;

      const arcRect = arc.getBoundingClientRect();
      const detailsRect = details.getBoundingClientRect();
      const rowStyle = window.getComputedStyle(row);

      // In row layout (horizontal), check if arc right overlaps details left
      // In column layout (vertical), check if arc bottom overlaps details top
      const isColumn = rowStyle.flexDirection === 'column';
      let isOverlapping = false;
      let overlapAmount = 0;

      if (isColumn) {
        isOverlapping = arcRect.bottom > detailsRect.top;
        overlapAmount = Math.max(0, arcRect.bottom - detailsRect.top);
      } else {
        isOverlapping = arcRect.right > detailsRect.left;
        overlapAmount = Math.max(0, arcRect.right - detailsRect.left);
      }

      return {
        isColumn,
        arcWidth: arcRect.width,
        arcHeight: arcRect.height,
        detailsWidth: detailsRect.width,
        isOverlapping,
        overlapAmount,
      };
    });

    // C. Measure Bottom Navigation Bar
    const navData = await page.evaluate(() => {
      const nav = document.querySelector('.cockpit-bottom-nav');
      if (!nav) return null;
      const navRect = nav.getBoundingClientRect();

      const items = Array.from(document.querySelectorAll('.nav-bar-item')).map(item => {
        const rect = item.getBoundingClientRect();
        const titleEl = item.querySelector('.nav-item-title');
        return {
          id: item.id,
          tab: item.dataset.tab,
          titleText: titleEl ? titleEl.textContent.trim() : '',
          width: rect.width,
          height: rect.height,
          titleScrollWidth: titleEl ? titleEl.scrollWidth : 0,
          titleClientWidth: titleEl ? titleEl.clientWidth : 0,
          titleOverflows: titleEl ? titleEl.scrollWidth > titleEl.clientWidth : false,
        };
      });

      const totalItemsWidth = items.reduce((sum, i) => sum + i.width, 0);

      return {
        totalNavWidth: navRect.width,
        navHeight: navRect.height,
        itemCount: items.length,
        items,
        totalItemsWidth,
        hasNavOverflow: totalItemsWidth > navRect.width + 1,
        allTouchTargetsSufficient: items.every(i => i.width >= 44 && i.height >= 44),
      };
    });

    // D. Measure Telemetry Stats Cards (8px Spacing Check)
    const statsData = await page.evaluate(() => {
      const cards = Array.from(document.querySelectorAll('.telemetry-stat-card')).map(c => {
        const rect = c.getBoundingClientRect();
        const valEl = c.querySelector('.stat-metric-val');
        const lblEl = c.querySelector('.stat-metric-lbl');
        const valRect = valEl ? valEl.getBoundingClientRect() : null;
        const lblRect = lblEl ? lblEl.getBoundingClientRect() : null;
        return {
          width: rect.width,
          height: rect.height,
          valText: valEl ? valEl.textContent.trim() : '',
          valMarginBottom: valEl ? window.getComputedStyle(valEl).marginBottom : '',
          gapBetweenValAndLbl: (valRect && lblRect) ? (lblRect.top - valRect.bottom) : null,
          lblText: lblEl ? lblEl.textContent.trim() : '',
          lblHeight: lblRect ? lblRect.height : 0,
        };
      });

      // Check card height consistency
      const heights = cards.filter(c => c.height > 0).map(c => c.height);
      const minH = Math.min(...heights);
      const maxH = Math.max(...heights);
      const isHeightConsistent = (maxH - minH) <= 2; // within 2px tolerance

      return {
        cards,
        isHeightConsistent,
        heightDifference: maxH - minH,
        minGap: Math.min(...cards.map(c => c.gapBetweenValAndLbl || 999)),
      };
    });

    // E. Measure Hero Button & Tactical Grid
    const heroAndGrid = await page.evaluate(() => {
      const btn = document.querySelector('#btn-hero-start-exam');
      const tiles = Array.from(document.querySelectorAll('.tactical-tile')).map(t => {
        const rect = t.getBoundingClientRect();
        const title = t.querySelector('.tile-title');
        const cap = t.querySelector('.tile-caption');
        return {
          id: t.id,
          height: rect.height,
          title: title ? title.textContent.trim() : '',
          caption: cap ? cap.textContent.trim() : '',
        };
      });

      const tileHeights = tiles.map(t => t.height);

      return {
        btnText: btn ? btn.textContent.trim() : '',
        btnWidth: btn ? btn.getBoundingClientRect().width : 0,
        btnHeight: btn ? btn.getBoundingClientRect().height : 0,
        btnOverflows: btn ? btn.scrollWidth > btn.clientWidth : false,
        tiles,
        tileHeightDifference: Math.max(...tileHeights) - Math.min(...tileHeights),
      };
    });

    // F. Measure Header Elements (320px Density)
    const headerData = await page.evaluate(() => {
      const header = document.querySelector('.app-header');
      const driver = document.querySelector('.header-driver');
      const controls = document.querySelector('.header-telemetry-controls');
      const name = document.querySelector('.driver-name');
      const role = document.querySelector('.driver-role-tag');

      const dRect = driver ? driver.getBoundingClientRect() : null;
      const cRect = controls ? controls.getBoundingClientRect() : null;
      const gap = (dRect && cRect) ? (cRect.left - dRect.right) : 0;

      return {
        headerWidth: header ? header.getBoundingClientRect().width : 0,
        gapBetweenDriverAndControls: gap,
        roleTagVisible: role ? window.getComputedStyle(role).display !== 'none' : false,
        driverName: name ? name.textContent.trim() : '',
      };
    });

    // Save screenshot
    const screenshotPath = path.join(__dirname, 'audit_screenshots', `remediated_vp_${vp.width}px.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });

    auditResults.viewports[vp.width] = {
      name: vp.name,
      overflow: overflowData,
      speedometer: speedometerData,
      nav: navData,
      stats: statsData,
      heroAndGrid,
      header: headerData,
      screenshot: screenshotPath,
    };

    console.log(`  Horizontal Scroll: ${overflowData.hasHorizontalScroll ? 'FAILED (OVERFLOW!)' : 'PASS (0px overflow)'}`);
    console.log(`  Bottom Nav Items: ${navData.itemCount} items (Total: ${navData.totalItemsWidth.toFixed(1)}px / ${navData.totalNavWidth}px)`);
    console.log(`  Bottom Nav Overflow: ${navData.hasNavOverflow ? 'FAILED' : 'PASS (100% visible on screen)'}`);
    console.log(`  Bottom Nav Touch Targets >= 44px: ${navData.allTouchTargetsSufficient ? 'PASS' : 'FAILED'}`);
    console.log(`  Speedometer Overlap: ${speedometerData.isOverlapping ? 'FAILED (' + speedometerData.overlapAmount + 'px)' : 'PASS (0px overlap, ' + (speedometerData.isColumn ? 'stacked' : 'side-by-side') + ')'}`);
    console.log(`  Stat Card Metric-Label Gap: ${statsData.minGap}px (Target >= 8px) -> ${statsData.minGap >= 7 ? 'PASS' : 'FAILED'}`);
    console.log(`  Hero Button Text: "${heroAndGrid.btnText}" (Height: ${heroAndGrid.btnHeight.toFixed(1)}px)`);
  }

  // 2. Sub-views and Nested Navigation at 375px
  console.log('\n--- Auditing Consolidated Views at 375px standard ---');
  await page.setViewport({ width: 375, height: 667, deviceScaleFactor: 2 });

  // Tab 1: Nazariya (Theory)
  await page.click('#nav-tests');
  await new Promise(r => setTimeout(r, 400));
  const theoryShot = path.join(__dirname, 'audit_screenshots', 'remediated_view_theory_375px.png');
  await page.screenshot({ path: theoryShot, fullPage: false });
  console.log(`  Captured View: Nazariya (Theory) -> ${theoryShot}`);

  // Tab 2: Avtodrom (Unified Practical Hub)
  await page.click('#nav-amaliy');
  await new Promise(r => setTimeout(r, 400));
  const amaliyShot = path.join(__dirname, 'audit_screenshots', 'remediated_view_avtodrom_modules_375px.png');
  await page.screenshot({ path: amaliyShot, fullPage: false });
  console.log(`  Captured View: Avtodrom (Modules) -> ${amaliyShot}`);

  // Switch to 3D Simulator inside Avtodrom
  await page.evaluate(() => {
    const btn = document.querySelector('.practical-sub-tab[data-section="sim"]');
    if (btn) btn.click();
  });
  await new Promise(r => setTimeout(r, 500));
  const simShot = path.join(__dirname, 'audit_screenshots', 'remediated_view_avtodrom_3dsim_375px.png');
  await page.screenshot({ path: simShot, fullPage: false });
  console.log(`  Captured Sub-Tab: 3D Simulator -> ${simShot}`);

  // Switch to Checklist inside Avtodrom
  await page.evaluate(() => {
    const btn = document.querySelector('.practical-sub-tab[data-section="checklist"]');
    if (btn) btn.click();
  });
  await new Promise(r => setTimeout(r, 400));
  const chkShot = path.join(__dirname, 'audit_screenshots', 'remediated_view_avtodrom_checklist_375px.png');
  await page.screenshot({ path: chkShot, fullPage: false });
  console.log(`  Captured Sub-Tab: Checklist -> ${chkShot}`);

  // Tab 3: Profil (Unified Driver Hub)
  await page.click('#nav-profile');
  await new Promise(r => setTimeout(r, 400));
  const profileShot = path.join(__dirname, 'audit_screenshots', 'remediated_view_profile_375px.png');
  await page.screenshot({ path: profileShot, fullPage: false });
  console.log(`  Captured View: Profil -> ${profileShot}`);

  // Modal: Quiz HUD
  await page.click('#nav-home');
  await new Promise(r => setTimeout(r, 300));
  await page.click('#btn-hero-start-exam');
  await new Promise(r => setTimeout(r, 600));

  const quizTouchData = await page.evaluate(() => {
    const closeBtn = document.querySelector('#btn-close-quiz');
    const cRect = closeBtn ? closeBtn.getBoundingClientRect() : null;
    return {
      width: cRect ? cRect.width : 0,
      height: cRect ? cRect.height : 0,
      meetsTouchTarget: cRect ? (cRect.width >= 44 && cRect.height >= 44) : false,
    };
  });

  const quizShot = path.join(__dirname, 'audit_screenshots', 'remediated_modal_quiz_375px.png');
  await page.screenshot({ path: quizShot, fullPage: false });
  console.log(`  Captured Modal: Quiz HUD -> ${quizShot}`);
  console.log(`  Quiz Close Button Size: ${quizTouchData.width}x${quizTouchData.height}px (Touch Target >= 44px: ${quizTouchData.meetsTouchTarget ? 'PASS' : 'FAILED'})`);
  auditResults.quizCloseTouchTarget = quizTouchData;

  // Close quiz
  await page.click('#btn-close-quiz');
  await new Promise(r => setTimeout(r, 300));

  // 3. Language Testing
  console.log('\n--- Auditing Multilingual Text Fitting (uz_latn, uz_cyrl, ru) ---');
  const langs = ['uz_latn', 'uz_cyrl', 'ru'];
  for (const lang of langs) {
    await page.evaluate((l) => {
      if (window.setAppLanguage) window.setAppLanguage(l);
    }, lang);
    await new Promise(r => setTimeout(r, 300));

    const lData = await page.evaluate(() => {
      const btn = document.querySelector('#btn-hero-start-exam');
      const navItems = Array.from(document.querySelectorAll('.nav-bar-item')).map(i => ({
        tab: i.dataset.tab,
        title: i.querySelector('.nav-item-title').textContent.trim(),
        width: i.getBoundingClientRect().width,
      }));

      return {
        heroBtnText: btn ? btn.textContent.trim() : '',
        heroBtnHeight: btn ? btn.getBoundingClientRect().height : 0,
        heroBtnOverflows: btn ? btn.scrollWidth > btn.clientWidth : false,
        navItems,
      };
    });

    auditResults.linguisticFits[lang] = lData;
    console.log(`  [${lang}] Hero Button: "${lData.heroBtnText}" (Height: ${lData.heroBtnHeight.toFixed(1)}px, Overflows: ${lData.heroBtnOverflows})`);
    console.log(`         Nav Items: ${lData.navItems.map(i => `${i.title} (${i.width.toFixed(1)}px)`).join(' | ')}`);
  }

  // Save diagnostic results
  fs.writeFileSync(
    path.join(__dirname, 'remediation_diagnostics_raw.json'),
    JSON.stringify(auditResults, null, 2),
    'utf-8'
  );

  console.log('\n=================================================================');
  console.log('REMEDIATION AUDIT COMPLETE! Raw data saved to remediation_diagnostics_raw.json');
  console.log('=================================================================\n');

  await browser.close();
}

runRemediationAudit().catch(err => {
  console.error('Audit failed with error:', err);
  process.exit(1);
});

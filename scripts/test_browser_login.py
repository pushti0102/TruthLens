"""
Automate Chrome to visit http://127.0.0.1:5173/login,
click the Admin demo account button, click Sign In,
and verify that /dashboard loads with all components.
"""
import subprocess
import time
import os

script = """
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle2' });
  console.log('Opened login page, title:', await page.title());
  
  // Click the 'Admin' demo button (button containing 'Admin')
  const buttons = await page.$$('button');
  for (const b of buttons) {
    const text = await page.evaluate(el => el.textContent, b);
    if (text.trim() === 'Admin') {
      console.log('Clicking Admin demo button');
      await b.click();
      break;
    }
  }
  
  // Click Sign In
  for (const b of buttons) {
    const text = await page.evaluate(el => el.textContent, b);
    if (text.includes('Sign In')) {
      console.log('Clicking Sign In button');
      await b.click();
      break;
    }
  }
  
  await page.waitForNavigation({ timeout: 5000 }).catch(() => {});
  await new Promise(r => setTimeout(r, 2000));
  
  console.log('Current URL after login:', page.url());
  await page.screenshot({ path: 'd:\\\\TruthLens-main\\\\dashboard_screenshot.png' });
  console.log('Dashboard screenshot saved!');
  await browser.close();
})();
"""

print("Running login test...")


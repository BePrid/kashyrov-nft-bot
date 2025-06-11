const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto('https://web.telegram.org/');

  console.log("Открыл Telegram Web. Войди в свой аккаунт вручную.");
})();

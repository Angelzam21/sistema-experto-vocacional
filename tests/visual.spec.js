// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('ORIENTAI — regresión visual', () => {
  test.beforeEach(async ({ page }) => {
    // Carga la app y espera a que el contenido sea visible.
    await page.goto('/');
    await page.waitForSelector('button', { timeout: 15_000 });
    // Espera adicional para que Inter (Google Fonts) y el CSS inyectado terminen de aplicar.
    await page.waitForTimeout(1500);
  });

  test('pantalla de bienvenida muestra el logo ORIENTAI', async ({ page }) => {
    // El SVG del logo tiene aria-label="ORIENTAI".
    await expect(page.locator('[aria-label="ORIENTAI"]')).toBeVisible();
    await expect(page).toHaveScreenshot('orientai-welcome.png', {
      maxDiffPixelRatio: 0.03,
    });
  });

  test('quiz: opción seleccionada muestra feedback visual correcto', async ({ page }) => {
    // Navega a la pantalla del test.
    await page.getByRole('button', { name: /comenzar/i }).click();
    await page.waitForSelector('div[role="radiogroup"]', { timeout: 10_000 });
    await page.waitForTimeout(1000);

    // Captura del estado inicial: la opción 3 (Me da igual) debe aparecer
    // con fondo --violet ya que es el valor por defecto (input:checked).
    await expect(page).toHaveScreenshot('orientai-quiz-default.png', {
      maxDiffPixelRatio: 0.03,
    });

    // Selecciona la opción 5 (Me encantaría) haciendo click.
    const labels = page.locator('div[role="radiogroup"] > label');
    await labels.nth(4).click();
    await page.waitForTimeout(600);

    // Captura post-click: opción 5 debe tener fondo --violet y sombra 0.
    await expect(page).toHaveScreenshot('orientai-quiz-selected.png', {
      maxDiffPixelRatio: 0.03,
    });
  });
});

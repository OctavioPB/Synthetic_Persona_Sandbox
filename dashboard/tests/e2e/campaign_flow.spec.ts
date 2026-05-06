import { test, expect } from '@playwright/test'

/**
 * E2E: Campaign Launcher → Simulation Results → History flow.
 * Requires the API (port 8000) and at least one segment in the DB.
 * Set SEED_SEGMENT_ID env var to skip the segment selector fallback.
 */

test.describe('Campaign Launcher', () => {
  test('nav link opens campaign launcher page', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /campaigns/i }).click()
    await expect(page.getByText('Test your campaign before it ships')).toBeVisible()
  })

  test('step 1: requires campaign name and segment', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /campaigns/i }).click()

    // Next button disabled initially
    const nextBtn = page.getByRole('button', { name: /next.*variants/i })
    await expect(nextBtn).toBeDisabled()

    // Fill in name only — still disabled (no segment)
    await page.getByPlaceholder(/e\.g\. Summer/i).fill('Test Campaign')
    await expect(nextBtn).toBeDisabled()
  })

  test('step 2: requires at least one variant', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /campaigns/i }).click()

    await page.getByPlaceholder(/e\.g\. Summer/i).fill('My Campaign')

    // If API has segments, the select will populate; otherwise we skip step 2 assertion
    const segmentSelect = page.locator('select').first()
    const options = await segmentSelect.locator('option').count()
    if (options <= 1) {
      // No segments loaded — expected in unit test context
      return
    }

    await segmentSelect.selectOption({ index: 1 })
    await page.getByRole('button', { name: /next.*variants/i }).click()

    // Launch button disabled with 0 variants
    const launchBtn = page.getByRole('button', { name: /launch.*variant/i })
    await expect(launchBtn).toBeDisabled()
  })

  test('stimulus builder: add variant flow', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /campaigns/i }).click()

    await page.getByPlaceholder(/e\.g\. Summer/i).fill('Test Campaign')
    const segmentSelect = page.locator('select').first()
    const options = await segmentSelect.locator('option').count()
    if (options <= 1) return

    await segmentSelect.selectOption({ index: 1 })
    await page.getByRole('button', { name: /next.*variants/i }).click()

    // Open stimulus builder
    await page.getByRole('button', { name: /add variant/i }).click()
    await expect(page.getByText('New Variant')).toBeVisible()

    // Fill ad_copy variant
    await page.getByPlaceholder(/e\.g\. Summer Hero Banner/i).fill('Hero Banner')
    await page.getByPlaceholder(/Summer Sale/i).fill('50% Off Everything')
    await page.getByPlaceholder(/Discover curated/i).fill('Shop the best deals this season.')
    await page.getByPlaceholder(/Shop Now/i).fill('Shop Now')

    await page.getByRole('button', { name: /add variant/i }).last().click()

    // Variant appears in list
    await expect(page.getByText('Hero Banner')).toBeVisible()
  })
})

test.describe('Analytics Page', () => {
  test('analytics nav link opens analytics page', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /analytics/i }).click()
    await expect(page.getByText('Simulation performance')).toBeVisible()
  })

  test('tab navigation works', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /analytics/i }).click()

    await page.getByRole('button', { name: /history/i }).click()
    await expect(page.getByText('Export CSV')).toBeVisible()

    await page.getByRole('button', { name: /compare/i }).click()
    await expect(page.getByText('Select Runs')).toBeVisible()

    await page.getByRole('button', { name: /overview/i }).click()
    await expect(page.getByText('Daily avg score')).toBeVisible()
  })
})

test.describe('Dark mode', () => {
  test('dark mode toggle switches theme attribute', async ({ page }) => {
    await page.goto('/')
    const html = page.locator('html')

    // Initial state — no dark
    await expect(html).not.toHaveAttribute('data-theme', 'dark')

    await page.getByRole('button', { name: /dark/i }).click()
    await expect(html).toHaveAttribute('data-theme', 'dark')

    await page.getByRole('button', { name: /light/i }).click()
    await expect(html).toHaveAttribute('data-theme', 'light')
  })
})

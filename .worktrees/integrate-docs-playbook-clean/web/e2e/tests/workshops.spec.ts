import { test, expect } from '@playwright/test';

// Mock data for testing
const mockEngagementId = 'eng-test-001';
const mockWorkshop = {
  title: 'Test Security Workshop',
  attendees: [
    { user_id: 'user1', email: 'test1@example.com', role: 'Lead' },
    { user_id: 'user2', email: 'test2@example.com', role: 'Member' }
  ]
};

test.describe('Workshops Consent Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Set up demo auth
    await page.addInitScript(() => {
      localStorage.setItem('email', 'test1@example.com');
      localStorage.setItem('engagementId', 'eng-test-001');
    });
  });

  test('should display workshops list page', async ({ page }) => {
    // Mock the API response for workshops list
    await page.route('**/api/v1/workshops*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workshops: [],
          total_count: 0,
          page: 1,
          page_size: 50,
          has_more: false
        })
      });
    });

    await page.goto(`/e/${mockEngagementId}/workshops`);

    // Check page loads
    await expect(page.locator('h1')).toContainText('Workshops');
    await expect(page.locator('text=New Workshop')).toBeVisible();
    
    // Check empty state
    await expect(page.locator('text=No workshops')).toBeVisible();
    await expect(page.locator('text=Get started by creating a new workshop')).toBeVisible();
  });

  test('should create new workshop via modal', async ({ page }) => {
    let workshopCreated = false;

    // Mock workshops list (empty initially)
    await page.route('**/api/v1/workshops*', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            workshops: workshopCreated ? [{
              id: 'workshop-123',
              engagement_id: mockEngagementId,
              ...mockWorkshop,
              created_by: 'test1@example.com',
              created_at: new Date().toISOString(),
              started: false,
              attendees: mockWorkshop.attendees.map((att, i) => ({
                id: `attendee-${i}`,
                ...att,
                consent: undefined
              }))
            }] : [],
            total_count: workshopCreated ? 1 : 0,
            page: 1,
            page_size: 50,
            has_more: false
          })
        });
      } else if (route.request().method() === 'POST') {
        workshopCreated = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'workshop-123',
            engagement_id: mockEngagementId,
            ...mockWorkshop,
            created_by: 'test1@example.com',
            created_at: new Date().toISOString(),
            started: false,
            attendees: mockWorkshop.attendees.map((att, i) => ({
              id: `attendee-${i}`,
              ...att,
              consent: undefined
            }))
          })
        });
      }
    });

    await page.goto(`/e/${mockEngagementId}/workshops`);

    // Open new workshop modal
    await page.locator('button', { hasText: 'New Workshop' }).first().click();
    await expect(page.locator('text=New Workshop').nth(1)).toBeVisible();

    // Fill workshop form
    await page.fill('input[type="text"]', mockWorkshop.title);
    
    // Fill first attendee (pre-filled)
    await page.fill('input[type="email"]', mockWorkshop.attendees[0].email);
    await page.fill('input[placeholder="User ID"]', mockWorkshop.attendees[0].user_id);
    await page.selectOption('select', mockWorkshop.attendees[0].role);

    // Add second attendee
    await page.locator('button', { hasText: '+ Add Attendee' }).click();
    const emailInputs = page.locator('input[type="email"]');
    const userIdInputs = page.locator('input[placeholder="User ID"]');
    const roleSelects = page.locator('select');

    await emailInputs.nth(1).fill(mockWorkshop.attendees[1].email);
    await userIdInputs.nth(1).fill(mockWorkshop.attendees[1].user_id);
    await roleSelects.nth(1).selectOption(mockWorkshop.attendees[1].role);

    // Submit form
    await page.locator('button[type="submit"]').click();

    // Wait for modal to close and workshop to appear
    await expect(page.locator('text=New Workshop').nth(1)).not.toBeVisible();
    await expect(page.locator(`text=${mockWorkshop.title}`)).toBeVisible();
  });

  test('should navigate to workshop detail and show consent status', async ({ page }) => {
    const workshopWithConsent = {
      id: 'workshop-456',
      engagement_id: mockEngagementId,
      ...mockWorkshop,
      created_by: 'test1@example.com',
      created_at: new Date().toISOString(),
      started: false,
      attendees: [
        {
          id: 'attendee-0',
          ...mockWorkshop.attendees[0],
          consent: {
            by: 'test1@example.com',
            user_id: 'test1@example.com',
            timestamp: new Date().toISOString()
          }
        },
        {
          id: 'attendee-1',
          ...mockWorkshop.attendees[1],
          consent: undefined
        }
      ]
    };

    // Mock workshops list
    await page.route('**/api/v1/workshops*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workshops: [workshopWithConsent],
          total_count: 1,
          page: 1,
          page_size: 50,
          has_more: false
        })
      });
    });

    await page.goto(`/e/${mockEngagementId}/workshops`);
    
    // Click on workshop to go to detail page
    await page.locator(`text=${mockWorkshop.title}`).click();
    
    // Check we're on detail page
    await expect(page).toHaveURL(`/e/${mockEngagementId}/workshops/workshop-456`);
    await expect(page.locator('h1')).toContainText(mockWorkshop.title);
    
    // Check consent status
    await expect(page.locator('text=Consent Progress')).toBeVisible();
    await expect(page.locator('text=1/2 (50%)')).toBeVisible();
    
    // Check attendee rows
    await expect(page.locator('text=test1@example.com')).toBeVisible();
    await expect(page.locator('text=test2@example.com')).toBeVisible();
    await expect(page.locator('text=Consented')).toBeVisible();
    await expect(page.locator('text=Consent pending')).toBeVisible();

    // Start button should be disabled
    const startButton = page.locator('button', { hasText: 'Start Workshop' });
    await expect(startButton).toBeDisabled();
  });

  test('should give consent and enable start workshop', async ({ page }) => {
    const workshopId = 'workshop-789';
    let consentGiven = false;
    let workshopStarted = false;

    const getWorkshopData = () => ({
      id: workshopId,
      engagement_id: mockEngagementId,
      ...mockWorkshop,
      created_by: 'test1@example.com',
      created_at: new Date().toISOString(),
      started: workshopStarted,
      started_at: workshopStarted ? new Date().toISOString() : undefined,
      attendees: [
        {
          id: 'attendee-0',
          ...mockWorkshop.attendees[0],
          consent: {
            by: 'test1@example.com',
            user_id: 'test1@example.com',
            timestamp: new Date().toISOString()
          }
        },
        {
          id: 'attendee-1',
          ...mockWorkshop.attendees[1],
          consent: consentGiven ? {
            by: 'test2@example.com',
            user_id: 'test2@example.com',
            timestamp: new Date().toISOString()
          } : undefined
        }
      ]
    });

    // Mock workshops list
    await page.route('**/api/v1/workshops*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workshops: [getWorkshopData()],
          total_count: 1,
          page: 1,
          page_size: 50,
          has_more: false
        })
      });
    });

    // Mock consent endpoint
    await page.route(`**/api/v1/workshops/${workshopId}/consent`, async (route) => {
      consentGiven = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(getWorkshopData())
      });
    });

    // Mock start workshop endpoint
    await page.route(`**/api/v1/workshops/${workshopId}/start`, async (route) => {
      workshopStarted = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workshop: getWorkshopData(),
          message: 'Workshop started successfully'
        })
      });
    });

    // Set current user as second attendee to test consent
    await page.addInitScript(() => {
      localStorage.setItem('email', 'test2@example.com');
    });

    await page.goto(`/e/${mockEngagementId}/workshops/${workshopId}`);

    // Should see consent button for current user
    await expect(page.locator('button', { hasText: 'I Consent to Participate' })).toBeVisible();
    
    // Give consent
    await page.locator('button', { hasText: 'I Consent to Participate' }).click();
    
    // Wait for consent to be processed
    await expect(page.locator('text=2/2 (100%)')).toBeVisible();
    
    // Start button should now be enabled (but user2 is not lead, so they can't start)
    // Let's switch back to lead user
    await page.addInitScript(() => {
      localStorage.setItem('email', 'test1@example.com');
    });
    
    // Refresh page to get lead permissions
    await page.reload();
    
    // Now start workshop button should be enabled
    const startButton = page.locator('button', { hasText: 'Start Workshop' });
    await expect(startButton).not.toBeDisabled();
    
    await startButton.click();
    
    // Check workshop started
    await expect(page.locator('text=Started')).toBeVisible();
    await expect(page.locator('text=Workshop Started')).toBeVisible();
  });

  test('should handle 403 permission errors', async ({ page }) => {
    // Mock 403 response for workshops list
    await page.route('**/api/v1/workshops*', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Insufficient permissions'
        })
      });
    });

    await page.goto(`/e/${mockEngagementId}/workshops`);
    
    // Should show error message
    await expect(page.locator('text=Failed to load workshops')).toBeVisible();
  });

  test('should validate consent requirement before starting workshop', async ({ page }) => {
    const workshopId = 'workshop-validation';
    
    const workshopData = {
      id: workshopId,
      engagement_id: mockEngagementId,
      ...mockWorkshop,
      created_by: 'test1@example.com',
      created_at: new Date().toISOString(),
      started: false,
      attendees: [
        {
          id: 'attendee-0',
          ...mockWorkshop.attendees[0],
          consent: {
            by: 'test1@example.com',
            user_id: 'test1@example.com',
            timestamp: new Date().toISOString()
          }
        },
        {
          id: 'attendee-1',
          ...mockWorkshop.attendees[1],
          consent: undefined // No consent given
        }
      ]
    };

    // Mock workshops list
    await page.route('**/api/v1/workshops*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workshops: [workshopData],
          total_count: 1,
          page: 1,
          page_size: 50,
          has_more: false
        })
      });
    });

    // Mock start workshop endpoint to return 403 due to missing consent
    await page.route(`**/api/v1/workshops/${workshopId}/start`, async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Cannot start workshop: not all attendees have given consent'
        })
      });
    });

    await page.goto(`/e/${mockEngagementId}/workshops/${workshopId}`);

    // Start button should be disabled due to missing consent
    const startButton = page.locator('button', { hasText: 'Start Workshop' });
    await expect(startButton).toBeDisabled();
    
    // Should show validation message
    await expect(page.locator('text=All attendees must consent before workshop can start')).toBeVisible();
    
    // Progress should show incomplete
    await expect(page.locator('text=1/2 (50%)')).toBeVisible();
  });
});
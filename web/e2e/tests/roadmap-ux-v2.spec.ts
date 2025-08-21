import { test, expect, Page } from '@playwright/test';

/**
 * Comprehensive E2E tests for Roadmap UX v2
 * Tests feature flags, weight/cost adjustments, and resource profile updates
 */

// Test data configuration
const TEST_CONFIG = {
  ROADMAP_V2_FEATURE_FLAG: 'ROADMAP_V2',
  UX_ASSESSMENT_V2_FEATURE_FLAG: 'UX_ASSESSMENT_V2',
  DEFAULT_INITIATIVE_SIZE: 'M',
  PERFORMANCE_THRESHOLD_MS: 2000,
  DEFAULT_WAVE_DURATION: 12
};

// Mock assessment data for testing
const MOCK_ASSESSMENT_DATA = {
  id: 'test-assessment-123',
  name: 'Test Cybersecurity Assessment',
  engagement_id: 'test-engagement-456',
  categories: [
    {
      id: 'id-am',
      name: 'Identify: Asset Management',
      subcategories: [
        {
          id: 'id-am-1',
          name: 'ID.AM-1: Physical devices and systems within the organization are inventoried',
          score: 2.5,
          weight: 1.0
        },
        {
          id: 'id-am-2', 
          name: 'ID.AM-2: Software platforms and applications within the organization are inventoried',
          score: 3.0,
          weight: 1.2
        }
      ]
    }
  ]
};

// Helper functions
class RoadmapTestHelper {
  constructor(private page: Page) {}

  async navigateToRoadmap(engagementId: string) {
    await this.page.goto(`/e/${engagementId}/dashboard`);
    await this.page.click('[data-testid="roadmap-tab"]');
    await this.page.waitForSelector('[data-testid="roadmap-container"]');
  }

  async toggleFeatureFlag(flagName: string, enabled: boolean) {
    // Navigate to admin panel to toggle feature flags
    await this.page.goto('/admin/ops');
    await this.page.fill(`[data-testid="feature-flag-${flagName}"]`, enabled.toString());
    await this.page.click('[data-testid="save-feature-flags"]');
    await this.page.waitForSelector('[data-testid="feature-flags-saved"]');
  }

  async adjustWeightAndCost(categoryId: string, newWeight: number, newCost?: number) {
    const categoryRow = this.page.locator(`[data-testid="category-${categoryId}"]`);
    
    // Adjust weight
    await categoryRow.locator('[data-testid="weight-input"]').fill(newWeight.toString());
    
    // Adjust cost if provided
    if (newCost !== undefined) {
      await categoryRow.locator('[data-testid="cost-input"]').fill(newCost.toString());
    }
    
    // Apply changes
    await categoryRow.locator('[data-testid="apply-changes"]').click();
  }

  async verifyScoreUpdated(categoryId: string, expectedScore: number, tolerance: number = 0.1) {
    const scoreElement = this.page.locator(`[data-testid="score-${categoryId}"]`);
    const actualScore = parseFloat(await scoreElement.textContent() || '0');
    expect(Math.abs(actualScore - expectedScore)).toBeLessThan(tolerance);
  }

  async verifyWaveUpdated(waveNumber: number, expectedFte: number, expectedCost: number) {
    const waveElement = this.page.locator(`[data-testid="wave-${waveNumber}"]`);
    
    const fteText = await waveElement.locator('[data-testid="wave-fte"]').textContent();
    const costText = await waveElement.locator('[data-testid="wave-cost"]').textContent();
    
    const actualFte = parseFloat(fteText?.replace(/[^\d.]/g, '') || '0');
    const actualCost = parseFloat(costText?.replace(/[^\d.]/g, '') || '0');
    
    expect(Math.abs(actualFte - expectedFte)).toBeLessThan(0.5);
    expect(Math.abs(actualCost - expectedCost)).toBeLessThan(1000);
  }

  async updateResourceProfile(profileData: any) {
    await this.page.click('[data-testid="resource-profile-edit"]');
    
    // Update skill requirements
    for (const skill of profileData.skills) {
      await this.page.selectOption(`[data-testid="skill-${skill.name}"]`, skill.level);
    }
    
    // Update role allocations
    for (const role of profileData.roles) {
      await this.page.fill(`[data-testid="role-${role.type}-fte"]`, role.fte.toString());
      await this.page.fill(`[data-testid="role-${role.type}-duration"]`, role.duration.toString());
    }
    
    await this.page.click('[data-testid="save-resource-profile"]');
    await this.page.waitForSelector('[data-testid="resource-profile-saved"]');
  }

  async measurePerformance(action: () => Promise<void>): Promise<number> {
    const startTime = Date.now();
    await action();
    return Date.now() - startTime;
  }
}

test.describe('Roadmap UX v2 - Feature Flag Testing', () => {
  let helper: RoadmapTestHelper;

  test.beforeEach(async ({ page }) => {
    helper = new RoadmapTestHelper(page);
    
    // Set up test environment
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('test_mode', 'true');
      localStorage.setItem('mock_assessment_data', JSON.stringify(MOCK_ASSESSMENT_DATA));
    });
  });

  test('should enable ROADMAP_V2 feature flag and show new UI components', async ({ page }) => {
    // Toggle ROADMAP_V2 feature flag
    await helper.toggleFeatureFlag(TEST_CONFIG.ROADMAP_V2_FEATURE_FLAG, true);
    
    // Navigate to roadmap
    await helper.navigateToRoadmap(MOCK_ASSESSMENT_DATA.engagement_id);
    
    // Verify v2 UI components are visible
    await expect(page.locator('[data-testid="roadmap-v2-container"]')).toBeVisible();
    await expect(page.locator('[data-testid="wave-overlay-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="resource-profile-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid="skill-demand-forecast"]')).toBeVisible();
    
    // Verify legacy UI is hidden
    await expect(page.locator('[data-testid="roadmap-v1-container"]')).not.toBeVisible();
  });

  test('should disable ROADMAP_V2 feature flag and show legacy UI', async ({ page }) => {
    // Ensure ROADMAP_V2 feature flag is disabled
    await helper.toggleFeatureFlag(TEST_CONFIG.ROADMAP_V2_FEATURE_FLAG, false);
    
    // Navigate to roadmap
    await helper.navigateToRoadmap(MOCK_ASSESSMENT_DATA.engagement_id);
    
    // Verify legacy UI components are visible
    await expect(page.locator('[data-testid="roadmap-v1-container"]')).toBeVisible();
    
    // Verify v2 UI is hidden
    await expect(page.locator('[data-testid="roadmap-v2-container"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="wave-overlay-chart"]')).not.toBeVisible();
  });

  test('should enable UX_ASSESSMENT_V2 feature flag and enhance roadmap interactions', async ({ page }) => {
    // Enable both feature flags
    await helper.toggleFeatureFlag(TEST_CONFIG.ROADMAP_V2_FEATURE_FLAG, true);
    await helper.toggleFeatureFlag(TEST_CONFIG.UX_ASSESSMENT_V2_FEATURE_FLAG, true);
    
    // Navigate to roadmap
    await helper.navigateToRoadmap(MOCK_ASSESSMENT_DATA.engagement_id);
    
    // Verify enhanced UX features
    await expect(page.locator('[data-testid="interactive-weight-sliders"]')).toBeVisible();
    await expect(page.locator('[data-testid="real-time-score-updates"]')).toBeVisible();
    await expect(page.locator('[data-testid="drag-drop-prioritization"]')).toBeVisible();
    await expect(page.locator('[data-testid="advanced-filtering"]')).toBeVisible();
  });
});

test.describe('Roadmap UX v2 - Weight and Cost Adjustments', () => {
  let helper: RoadmapTestHelper;

  test.beforeEach(async ({ page }) => {
    helper = new RoadmapTestHelper(page);
    
    // Enable feature flags
    await helper.toggleFeatureFlag(TEST_CONFIG.ROADMAP_V2_FEATURE_FLAG, true);
    await helper.toggleFeatureFlag(TEST_CONFIG.UX_ASSESSMENT_V2_FEATURE_FLAG, true);
    
    // Set up test data
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('test_mode', 'true');
      localStorage.setItem('mock_assessment_data', JSON.stringify(MOCK_ASSESSMENT_DATA));
    });
    
    await helper.navigateToRoadmap(MOCK_ASSESSMENT_DATA.engagement_id);
  });

  test('should adjust weights and update scores in real-time', async ({ page }) => {
    const categoryId = 'id-am-1';
    const originalWeight = 1.0;
    const newWeight = 1.5;
    
    // Record original score
    const originalScoreText = await page.locator(`[data-testid="score-${categoryId}"]`).textContent();
    const originalScore = parseFloat(originalScoreText || '0');
    
    // Adjust weight
    await helper.adjustWeightAndCost(categoryId, newWeight);
    
    // Verify score updated in real-time
    await page.waitForTimeout(500); // Allow for real-time update
    const newScoreText = await page.locator(`[data-testid="score-${categoryId}"]`).textContent();
    const newScore = parseFloat(newScoreText || '0');
    
    // Score should change proportionally to weight change
    const expectedScore = originalScore * (newWeight / originalWeight);
    await helper.verifyScoreUpdated(categoryId, expectedScore);
    
    // Verify total score updated
    const totalScoreElement = page.locator('[data-testid="total-score"]');
    await expect(totalScoreElement).toContainText(/\d+\.\d+/);
  });

  test('should adjust costs and update wave allocations', async ({ page }) => {
    const categoryId = 'id-am-1';
    const newCost = 50000;
    
    // Record original wave costs
    const originalWave1Cost = await page.locator('[data-testid="wave-1"] [data-testid="wave-cost"]').textContent();
    
    // Adjust cost
    await helper.adjustWeightAndCost(categoryId, 1.0, newCost);
    
    // Verify wave costs updated
    await page.waitForTimeout(1000); // Allow for recalculation
    const newWave1Cost = await page.locator('[data-testid="wave-1"] [data-testid="wave-cost"]').textContent();
    
    expect(newWave1Cost).not.toBe(originalWave1Cost);
    
    // Verify cost is reflected in resource planning
    await expect(page.locator('[data-testid="total-estimated-cost"]')).toContainText(/\$[\d,]+/);
  });

  test('should update multiple categories and recalculate totals', async ({ page }) => {
    const adjustments = [
      { categoryId: 'id-am-1', weight: 1.3, cost: 45000 },
      { categoryId: 'id-am-2', weight: 0.8, cost: 35000 }
    ];
    
    // Apply multiple adjustments
    for (const adjustment of adjustments) {
      await helper.adjustWeightAndCost(adjustment.categoryId, adjustment.weight, adjustment.cost);
      await page.waitForTimeout(300); // Brief pause between adjustments
    }
    
    // Verify all totals recalculated
    await expect(page.locator('[data-testid="total-score"]')).toContainText(/\d+\.\d+/);
    await expect(page.locator('[data-testid="total-estimated-cost"]')).toContainText(/\$[\d,]+/);
    await expect(page.locator('[data-testid="total-fte-demand"]')).toContainText(/\d+\.\d+/);
    
    // Verify wave-level updates
    for (let waveNum = 1; waveNum <= 3; waveNum++) {
      await expect(page.locator(`[data-testid="wave-${waveNum}"] [data-testid="wave-cost"]`)).toContainText(/\$[\d,]+/);
      await expect(page.locator(`[data-testid="wave-${waveNum}"] [data-testid="wave-fte"]`)).toContainText(/\d+\.\d+/);
    }
  });
});

test.describe('Roadmap UX v2 - Resource Profile Updates', () => {
  let helper: RoadmapTestHelper;

  test.beforeEach(async ({ page }) => {
    helper = new RoadmapTestHelper(page);
    
    await helper.toggleFeatureFlag(TEST_CONFIG.ROADMAP_V2_FEATURE_FLAG, true);
    await helper.toggleFeatureFlag(TEST_CONFIG.UX_ASSESSMENT_V2_FEATURE_FLAG, true);
    
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('test_mode', 'true');
      localStorage.setItem('mock_assessment_data', JSON.stringify(MOCK_ASSESSMENT_DATA));
    });
    
    await helper.navigateToRoadmap(MOCK_ASSESSMENT_DATA.engagement_id);
  });

  test('should update resource profile and recalculate waves', async ({ page }) => {
    const newResourceProfile = {
      skills: [
        { name: 'cloud-security-architecture', level: 'expert' },
        { name: 'network-security', level: 'advanced' }
      ],
      roles: [
        { type: 'security-architect', fte: 1.5, duration: 16 },
        { type: 'security-engineer', fte: 2.0, duration: 12 }
      ]
    };
    
    // Update resource profile
    await helper.updateResourceProfile(newResourceProfile);
    
    // Verify resource profile changes reflected in waves
    await page.waitForTimeout(1000);
    
    // Check that FTE and costs updated based on new profile
    await expect(page.locator('[data-testid="wave-1"] [data-testid="wave-fte"]')).toContainText(/\d+\.\d+/);
    await expect(page.locator('[data-testid="skill-demand-chart"]')).toBeVisible();
    
    // Verify skill requirements shown in UI
    await expect(page.locator('[data-testid="required-skills-list"]')).toContainText('Cloud Security Architecture');
    await expect(page.locator('[data-testid="required-skills-list"]')).toContainText('Network Security');
  });

  test('should handle skill mapping and show availability', async ({ page }) => {
    // Click on skill mapping view
    await page.click('[data-testid="skill-mapping-view"]');
    
    // Verify skill mapping interface
    await expect(page.locator('[data-testid="skill-matrix"]')).toBeVisible();
    await expect(page.locator('[data-testid="availability-heatmap"]')).toBeVisible();
    
    // Check skill categories
    const skillCategories = ['technical', 'compliance', 'management', 'analytical'];
    for (const category of skillCategories) {
      await expect(page.locator(`[data-testid="skill-category-${category}"]`)).toBeVisible();
    }
    
    // Verify skill proficiency levels
    const proficiencyLevels = ['beginner', 'intermediate', 'advanced', 'expert'];
    for (const level of proficiencyLevels) {
      await expect(page.locator(`[data-testid="proficiency-${level}"]`)).toBeVisible();
    }
  });

  test('should export resource planning data', async ({ page }) => {
    // Click export button
    await page.click('[data-testid="export-resource-plan"]');
    
    // Select export format
    await page.selectOption('[data-testid="export-format"]', 'detailed');
    
    // Configure export options
    await page.check('[data-testid="include-skills"]');
    await page.check('[data-testid="include-costs"]');
    
    // Start export
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="start-export"]');
    
    // Verify download
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/resource_planning_detailed_\d{8}_\d{6}\.csv/);
  });
});

test.describe('Roadmap UX v2 - Performance Tests', () => {
  let helper: RoadmapTestHelper;

  test.beforeEach(async ({ page }) => {
    helper = new RoadmapTestHelper(page);
    
    await helper.toggleFeatureFlag(TEST_CONFIG.ROADMAP_V2_FEATURE_FLAG, true);
    await helper.toggleFeatureFlag(TEST_CONFIG.UX_ASSESSMENT_V2_FEATURE_FLAG, true);
    
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('test_mode', 'true');
      localStorage.setItem('mock_assessment_data', JSON.stringify(MOCK_ASSESSMENT_DATA));
    });
  });

  test('should load roadmap within performance threshold', async ({ page }) => {
    const loadTime = await helper.measurePerformance(async () => {
      await helper.navigateToRoadmap(MOCK_ASSESSMENT_DATA.engagement_id);
      await page.waitForSelector('[data-testid="roadmap-v2-container"]');
    });
    
    expect(loadTime).toBeLessThan(TEST_CONFIG.PERFORMANCE_THRESHOLD_MS);
  });

  test('should update scores within performance threshold', async ({ page }) => {
    await helper.navigateToRoadmap(MOCK_ASSESSMENT_DATA.engagement_id);
    
    const updateTime = await helper.measurePerformance(async () => {
      await helper.adjustWeightAndCost('id-am-1', 1.5);
      await page.waitForSelector('[data-testid="score-updated"]', { timeout: 2000 });
    });
    
    expect(updateTime).toBeLessThan(TEST_CONFIG.PERFORMANCE_THRESHOLD_MS);
  });

  test('should handle large datasets efficiently', async ({ page }) => {
    // Create large mock dataset
    const largeAssessmentData = {
      ...MOCK_ASSESSMENT_DATA,
      categories: Array.from({ length: 50 }, (_, i) => ({
        id: `category-${i}`,
        name: `Category ${i}`,
        subcategories: Array.from({ length: 10 }, (_, j) => ({
          id: `subcategory-${i}-${j}`,
          name: `Subcategory ${i}-${j}`,
          score: Math.random() * 5,
          weight: 1.0
        }))
      }))
    };
    
    await page.evaluate((data) => {
      localStorage.setItem('mock_assessment_data', JSON.stringify(data));
    }, largeAssessmentData);
    
    // Test performance with large dataset
    const renderTime = await helper.measurePerformance(async () => {
      await helper.navigateToRoadmap(MOCK_ASSESSMENT_DATA.engagement_id);
      await page.waitForSelector('[data-testid="roadmap-v2-container"]');
    });
    
    expect(renderTime).toBeLessThan(TEST_CONFIG.PERFORMANCE_THRESHOLD_MS * 2); // Allow 2x threshold for large data
    
    // Test scrolling performance
    const scrollTime = await helper.measurePerformance(async () => {
      await page.evaluate(() => {
        const container = document.querySelector('[data-testid="roadmap-v2-container"]');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
      await page.waitForTimeout(100);
    });
    
    expect(scrollTime).toBeLessThan(500); // Scrolling should be very fast
  });
});

test.describe('Roadmap UX v2 - Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    const helper = new RoadmapTestHelper(page);
    
    await helper.toggleFeatureFlag(TEST_CONFIG.ROADMAP_V2_FEATURE_FLAG, true);
    await helper.toggleFeatureFlag(TEST_CONFIG.UX_ASSESSMENT_V2_FEATURE_FLAG, true);
    
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('test_mode', 'true');
      localStorage.setItem('mock_assessment_data', JSON.stringify(MOCK_ASSESSMENT_DATA));
    });
    
    await helper.navigateToRoadmap(MOCK_ASSESSMENT_DATA.engagement_id);
  });

  test('should support keyboard navigation', async ({ page }) => {
    // Test tab navigation
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();
    
    // Test enter key on interactive elements
    await page.keyboard.press('Enter');
    await page.waitForTimeout(100);
    
    // Test arrow key navigation in grids
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowRight');
  });

  test('should have proper ARIA labels and roles', async ({ page }) => {
    // Check main container has proper role
    await expect(page.locator('[data-testid="roadmap-v2-container"]')).toHaveAttribute('role', 'main');
    
    // Check charts have proper labels
    await expect(page.locator('[data-testid="wave-overlay-chart"]')).toHaveAttribute('aria-label');
    
    // Check interactive elements have proper roles
    await expect(page.locator('[data-testid="weight-input"]').first()).toHaveAttribute('role', 'slider');
  });

  test('should support screen reader announcements', async ({ page }) => {
    // Check for live regions for dynamic updates
    await expect(page.locator('[aria-live="polite"]')).toBeVisible();
    
    // Test score update announcements
    const helper = new RoadmapTestHelper(page);
    await helper.adjustWeightAndCost('id-am-1', 1.5);
    
    // Verify announcement region updated
    const liveRegion = page.locator('[aria-live="polite"]');
    await expect(liveRegion).toContainText(/score updated/i);
  });
});
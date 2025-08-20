"""
Playwright E2E tests for Sprint v1.4 UAT Audio and PPTX features.
Tests user interactions through the web interface.
"""
import os
import pytest
import asyncio
import base64
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@pytest.mark.asyncio
class TestUATPlaywrightWorkflow:
    """Playwright E2E tests for UAT audio transcription and PPTX generation workflow."""
    
    @pytest.fixture(scope="session")
    async def browser(self):
        """Setup browser for testing."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=os.environ.get("HEADLESS", "true").lower() == "true",
                slow_mo=100 if os.environ.get("SLOW_MO") else None
            )
            yield browser
            await browser.close()
    
    @pytest.fixture
    async def context(self, browser: Browser):
        """Create browser context with UAT configuration."""
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="UAT-Test-Suite/1.0"
        )
        yield context
        await context.close()
    
    @pytest.fixture
    async def page(self, context: BrowserContext):
        """Create new page for testing."""
        page = await context.new_page()
        yield page
        await page.close()
    
    @pytest.fixture
    def sample_audio_file(self, tmp_path):
        """Create a sample audio file for upload testing."""
        # Create a minimal WAV file for testing
        wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00'
        wav_data = b'\x00' * 2000  # 2KB of audio data
        sample_wav = wav_header + wav_data
        
        audio_file = tmp_path / "test_workshop.wav"
        audio_file.write_bytes(sample_wav)
        return str(audio_file)
    
    @pytest.mark.asyncio
    async def test_uat_audio_transcription_ui_workflow(self, page: Page, sample_audio_file):
        """Test complete audio transcription workflow through UI."""
        # Assume the app is running on localhost:3000 (Next.js frontend)
        base_url = os.environ.get("UAT_BASE_URL", "http://localhost:3000")
        
        try:
            # Navigate to audio transcription page
            await page.goto(f"{base_url}/uat/audio-transcription")
            await page.wait_for_load_state("networkidle")
            
            # Verify page loaded correctly
            await expect(page.locator("h1")).to_contain_text("Audio Transcription")
            
            # Test file upload
            file_input = page.locator('input[type="file"]')
            await file_input.set_input_files(sample_audio_file)
            
            # Verify file was selected
            uploaded_file = page.locator('[data-testid="uploaded-file"]')
            await expect(uploaded_file).to_be_visible()
            await expect(uploaded_file).to_contain_text("test_workshop.wav")
            
            # Set consent options
            consent_checkbox = page.locator('[data-testid="consent-checkbox"]')
            await consent_checkbox.check()
            
            consent_type = page.locator('[data-testid="consent-type"]')
            await consent_type.select_option("workshop")
            
            # Set engagement ID
            engagement_input = page.locator('[data-testid="engagement-id"]')
            engagement_id = f"uat_playwright_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            await engagement_input.fill(engagement_id)
            
            # Configure transcription options
            language_select = page.locator('[data-testid="language-select"]')
            await language_select.select_option("auto")
            
            timestamps_checkbox = page.locator('[data-testid="include-timestamps"]')
            await timestamps_checkbox.check()
            
            pii_scrub_checkbox = page.locator('[data-testid="pii-scrub"]')
            await pii_scrub_checkbox.check()
            
            # Start transcription
            transcribe_button = page.locator('[data-testid="transcribe-button"]')
            await transcribe_button.click()
            
            # Wait for processing
            processing_indicator = page.locator('[data-testid="processing"]')
            await expect(processing_indicator).to_be_visible()
            
            # Wait for results (with timeout)
            transcript_result = page.locator('[data-testid="transcript-result"]')
            await expect(transcript_result).to_be_visible(timeout=30000)
            
            # Verify transcription results
            transcript_text = page.locator('[data-testid="transcript-text"]')
            await expect(transcript_text).to_be_visible()
            
            confidence_score = page.locator('[data-testid="confidence-score"]')
            await expect(confidence_score).to_be_visible()
            
            # Check PII scrubbing report if enabled
            pii_report = page.locator('[data-testid="pii-report"]')
            if await pii_report.is_visible():
                redactions_count = page.locator('[data-testid="redactions-count"]')
                await expect(redactions_count).to_be_visible()
            
            # Test download functionality
            download_button = page.locator('[data-testid="download-transcript"]')
            if await download_button.is_visible():
                async with page.expect_download() as download_info:
                    await download_button.click()
                download = await download_info.value
                assert download.suggested_filename.endswith('.txt') or download.suggested_filename.endswith('.json')
            
            # Test copy to clipboard
            copy_button = page.locator('[data-testid="copy-transcript"]')
            if await copy_button.is_visible():
                await copy_button.click()
                
                # Verify copy success notification
                copy_notification = page.locator('[data-testid="copy-success"]')
                await expect(copy_notification).to_be_visible(timeout=5000)
        
        except Exception as e:
            # Take screenshot on failure for debugging
            await page.screenshot(path=f"uat_audio_failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            raise e
    
    @pytest.mark.asyncio
    async def test_uat_pptx_generation_ui_workflow(self, page: Page):
        """Test PPTX generation workflow through UI."""
        base_url = os.environ.get("UAT_BASE_URL", "http://localhost:3000")
        
        try:
            # Navigate to PPTX generation page
            await page.goto(f"{base_url}/uat/pptx-generation")
            await page.wait_for_load_state("networkidle")
            
            # Verify page loaded
            await expect(page.locator("h1")).to_contain_text("Executive Presentation")
            
            # Set engagement ID
            engagement_input = page.locator('[data-testid="engagement-id"]')
            engagement_id = f"uat_pptx_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            await engagement_input.fill(engagement_id)
            
            # Configure presentation options
            title_input = page.locator('[data-testid="presentation-title"]')
            await title_input.fill("UAT Test Cyber Maturity Roadmap")
            
            author_input = page.locator('[data-testid="presentation-author"]')
            await author_input.fill("UAT Test Suite")
            
            template_select = page.locator('[data-testid="template-select"]')
            await template_select.select_option("executive")
            
            # Input roadmap data (could be via form or JSON upload)
            roadmap_textarea = page.locator('[data-testid="roadmap-data"]')
            sample_roadmap = {
                "current_maturity": "Level 2",
                "target_maturity": "Level 4",
                "initiative_count": 12,
                "investment_required": "$500K"
            }
            await roadmap_textarea.fill(json.dumps(sample_roadmap, indent=2))
            
            # Alternatively, test JSON file upload
            json_upload = page.locator('[data-testid="roadmap-upload"]')
            if await json_upload.is_visible():
                # Create temporary JSON file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(sample_roadmap, f)
                    temp_json_file = f.name
                
                await json_upload.set_input_files(temp_json_file)
                os.unlink(temp_json_file)  # Clean up
            
            # Configure output options
            output_format = page.locator('[data-testid="output-format"]')
            await output_format.select_option("base64")
            
            # Generate presentation
            generate_button = page.locator('[data-testid="generate-button"]')
            await generate_button.click()
            
            # Wait for generation
            generation_progress = page.locator('[data-testid="generation-progress"]')
            await expect(generation_progress).to_be_visible()
            
            # Wait for completion
            generation_result = page.locator('[data-testid="generation-result"]')
            await expect(generation_result).to_be_visible(timeout=60000)  # PPTX generation can take time
            
            # Verify generation metadata
            slide_count = page.locator('[data-testid="slide-count"]')
            await expect(slide_count).to_be_visible()
            
            file_size = page.locator('[data-testid="file-size"]')
            await expect(file_size).to_be_visible()
            
            # Test download
            download_button = page.locator('[data-testid="download-pptx"]')
            async with page.expect_download() as download_info:
                await download_button.click()
            download = await download_info.value
            assert download.suggested_filename.endswith('.pptx')
            
            # Verify file size is reasonable
            download_path = await download.path()
            file_stats = os.stat(download_path)
            assert file_stats.st_size > 100000  # At least 100KB
            assert file_stats.st_size < 50000000  # Less than 50MB
            
            # Test preview functionality if available
            preview_button = page.locator('[data-testid="preview-pptx"]')
            if await preview_button.is_visible():
                await preview_button.click()
                
                preview_modal = page.locator('[data-testid="preview-modal"]')
                await expect(preview_modal).to_be_visible()
                
                # Check slide thumbnails
                slide_thumbnails = page.locator('[data-testid="slide-thumbnail"]')
                await expect(slide_thumbnails.first).to_be_visible()
        
        except Exception as e:
            await page.screenshot(path=f"uat_pptx_failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            raise e
    
    @pytest.mark.asyncio
    async def test_uat_integrated_workflow_ui(self, page: Page, sample_audio_file):
        """Test integrated workflow: Upload audio → Transcribe → Generate PPTX."""
        base_url = os.environ.get("UAT_BASE_URL", "http://localhost:3000")
        
        try:
            # Navigate to integrated workflow page
            await page.goto(f"{base_url}/uat/integrated-workflow")
            await page.wait_for_load_state("networkidle")
            
            engagement_id = f"uat_integrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Step 1: Audio Upload and Transcription
            step1_section = page.locator('[data-testid="step-1-audio"]')
            await expect(step1_section).to_be_visible()
            
            engagement_input = step1_section.locator('[data-testid="engagement-id"]')
            await engagement_input.fill(engagement_id)
            
            file_input = step1_section.locator('input[type="file"]')
            await file_input.set_input_files(sample_audio_file)
            
            consent_checkbox = step1_section.locator('[data-testid="consent-checkbox"]')
            await consent_checkbox.check()
            
            transcribe_button = step1_section.locator('[data-testid="transcribe-button"]')
            await transcribe_button.click()
            
            # Wait for transcription to complete
            step1_complete = page.locator('[data-testid="step-1-complete"]')
            await expect(step1_complete).to_be_visible(timeout=30000)
            
            # Step 2: Minutes Processing
            step2_section = page.locator('[data-testid="step-2-processing"]')
            await expect(step2_section).to_be_visible()
            
            process_button = step2_section.locator('[data-testid="process-minutes"]')
            await process_button.click()
            
            step2_complete = page.locator('[data-testid="step-2-complete"]')
            await expect(step2_complete).to_be_visible(timeout=15000)
            
            # Verify extracted insights
            suggested_assessments = page.locator('[data-testid="suggested-assessments"]')
            await expect(suggested_assessments).to_be_visible()
            
            identified_gaps = page.locator('[data-testid="identified-gaps"]')
            await expect(identified_gaps).to_be_visible()
            
            # Step 3: PPTX Generation
            step3_section = page.locator('[data-testid="step-3-pptx"]')
            await expect(step3_section).to_be_visible()
            
            # Configure presentation
            title_input = step3_section.locator('[data-testid="presentation-title"]')
            await title_input.fill(f"Workshop Analysis Results - {engagement_id}")
            
            generate_pptx_button = step3_section.locator('[data-testid="generate-pptx"]')
            await generate_pptx_button.click()
            
            step3_complete = page.locator('[data-testid="step-3-complete"]')
            await expect(step3_complete).to_be_visible(timeout=60000)
            
            # Step 4: Final Review and Download
            final_section = page.locator('[data-testid="final-review"]')
            await expect(final_section).to_be_visible()
            
            # Download all artifacts
            download_transcript = page.locator('[data-testid="download-transcript"]')
            download_insights = page.locator('[data-testid="download-insights"]')
            download_presentation = page.locator('[data-testid="download-presentation"]')
            
            downloads = []
            
            # Download transcript
            async with page.expect_download() as download_info:
                await download_transcript.click()
            downloads.append(await download_info.value)
            
            # Download insights
            async with page.expect_download() as download_info:
                await download_insights.click()
            downloads.append(await download_info.value)
            
            # Download presentation
            async with page.expect_download() as download_info:
                await download_presentation.click()
            downloads.append(await download_info.value)
            
            # Verify all downloads
            assert len(downloads) == 3
            assert any(d.suggested_filename.endswith('.txt') for d in downloads)
            assert any(d.suggested_filename.endswith('.json') for d in downloads)
            assert any(d.suggested_filename.endswith('.pptx') for d in downloads)
            
            # Test workflow summary
            workflow_summary = page.locator('[data-testid="workflow-summary"]')
            await expect(workflow_summary).to_be_visible()
            
            total_time = page.locator('[data-testid="total-processing-time"]')
            await expect(total_time).to_be_visible()
            
        except Exception as e:
            await page.screenshot(path=f"uat_integrated_failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            raise e
    
    @pytest.mark.asyncio
    async def test_uat_error_scenarios_ui(self, page: Page):
        """Test error handling scenarios in the UI."""
        base_url = os.environ.get("UAT_BASE_URL", "http://localhost:3000")
        
        try:
            # Test invalid file upload
            await page.goto(f"{base_url}/uat/audio-transcription")
            await page.wait_for_load_state("networkidle")
            
            # Create an invalid file (text file with .wav extension)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(b'This is not audio data')
                invalid_audio_file = f.name
            
            file_input = page.locator('input[type="file"]')
            await file_input.set_input_files(invalid_audio_file)
            
            consent_checkbox = page.locator('[data-testid="consent-checkbox"]')
            await consent_checkbox.check()
            
            engagement_input = page.locator('[data-testid="engagement-id"]')
            await engagement_input.fill("error_test")
            
            transcribe_button = page.locator('[data-testid="transcribe-button"]')
            await transcribe_button.click()
            
            # Should show error message
            error_message = page.locator('[data-testid="error-message"]')
            await expect(error_message).to_be_visible(timeout=10000)
            await expect(error_message).to_contain_text("error")
            
            os.unlink(invalid_audio_file)  # Clean up
            
            # Test missing required fields
            await page.reload()
            await page.wait_for_load_state("networkidle")
            
            # Try to submit without consent
            transcribe_button = page.locator('[data-testid="transcribe-button"]')
            await transcribe_button.click()
            
            # Should show validation error
            validation_error = page.locator('[data-testid="validation-error"]')
            await expect(validation_error).to_be_visible()
            
            # Test network error simulation
            # This would require mocking the network or having the backend return errors
            
        except Exception as e:
            await page.screenshot(path=f"uat_error_failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            raise e
    
    @pytest.mark.asyncio
    async def test_uat_accessibility_compliance(self, page: Page):
        """Test accessibility compliance for UAT features."""
        base_url = os.environ.get("UAT_BASE_URL", "http://localhost:3000")
        
        # Test audio transcription page accessibility
        await page.goto(f"{base_url}/uat/audio-transcription")
        await page.wait_for_load_state("networkidle")
        
        # Check for proper heading structure
        h1_elements = page.locator('h1')
        await expect(h1_elements).to_have_count(1)
        
        # Check form labels
        form_inputs = page.locator('input, select, textarea')
        input_count = await form_inputs.count()
        
        for i in range(input_count):
            input_element = form_inputs.nth(i)
            # Each input should have either a label or aria-label
            input_id = await input_element.get_attribute('id')
            aria_label = await input_element.get_attribute('aria-label')
            
            if input_id:
                label_for_input = page.locator(f'label[for="{input_id}"]')
                if not await label_for_input.is_visible():
                    assert aria_label is not None, f"Input at index {i} lacks proper labeling"
        
        # Check keyboard navigation
        first_input = page.locator('input').first
        await first_input.focus()
        
        # Tab through form elements
        await page.keyboard.press('Tab')
        focused_element = page.locator(':focus')
        await expect(focused_element).to_be_visible()
        
        # Check color contrast (basic check)
        # This is a simplified check - in practice you'd use axe-core or similar
        error_elements = page.locator('[data-testid="error-message"]')
        if await error_elements.is_visible():
            color = await error_elements.evaluate('getComputedStyle(this).color')
            # Basic check that error text isn't too light
            assert 'rgb(255, 255, 255)' not in color  # Not pure white
    
    @pytest.mark.asyncio
    async def test_uat_responsive_design(self, browser: Browser):
        """Test responsive design across different viewport sizes."""
        # Test mobile viewport
        mobile_context = await browser.new_context(
            viewport={"width": 375, "height": 667}  # iPhone SE
        )
        mobile_page = await mobile_context.new_page()
        
        base_url = os.environ.get("UAT_BASE_URL", "http://localhost:3000")
        
        try:
            await mobile_page.goto(f"{base_url}/uat/audio-transcription")
            await mobile_page.wait_for_load_state("networkidle")
            
            # Check mobile navigation
            mobile_nav = mobile_page.locator('[data-testid="mobile-nav"]')
            if await mobile_nav.is_visible():
                await expect(mobile_nav).to_be_visible()
            
            # Check form layout on mobile
            form_container = mobile_page.locator('[data-testid="transcription-form"]')
            await expect(form_container).to_be_visible()
            
            # Verify elements don't overflow
            viewport_width = 375
            all_elements = mobile_page.locator('*')
            element_count = await all_elements.count()
            
            # Sample check of first 10 elements
            for i in range(min(10, element_count)):
                element = all_elements.nth(i)
                if await element.is_visible():
                    box = await element.bounding_box()
                    if box:
                        assert box['x'] + box['width'] <= viewport_width + 10  # 10px tolerance
            
        finally:
            await mobile_page.close()
            await mobile_context.close()
        
        # Test tablet viewport
        tablet_context = await browser.new_context(
            viewport={"width": 768, "height": 1024}  # iPad
        )
        tablet_page = await tablet_context.new_page()
        
        try:
            await tablet_page.goto(f"{base_url}/uat/pptx-generation")
            await tablet_page.wait_for_load_state("networkidle")
            
            # Verify tablet layout
            main_content = tablet_page.locator('main')
            await expect(main_content).to_be_visible()
            
            # Check that sidebar or navigation adapts properly
            nav_elements = tablet_page.locator('nav')
            if await nav_elements.count() > 0:
                await expect(nav_elements.first).to_be_visible()
            
        finally:
            await tablet_page.close()
            await tablet_context.close()


# Helper function for expect - this would typically be imported from playwright
async def expect(locator):
    """Simple expect implementation for Playwright."""
    from playwright.async_api import expect as playwright_expect
    return playwright_expect(locator)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--browser", "chromium"])
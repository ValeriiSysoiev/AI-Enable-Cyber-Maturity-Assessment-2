/**
 * Tests for XSS sanitization utilities
 */

import { describe, it, expect } from '@jest/globals';
import {
  sanitizeHTML,
  sanitizeUserContent,
  escapeHTML,
  highlightTextSafely,
  sanitizeURL,
  sanitizeDataAttribute,
  sanitizeJSON,
  needsSanitization
} from '../lib/sanitizer';

describe('XSS Sanitization', () => {
  describe('sanitizeHTML', () => {
    it('should allow safe HTML tags', () => {
      const input = '<mark class="bg-yellow-200">highlighted</mark> text';
      const result = sanitizeHTML(input);
      expect(result).toContain('<mark');
      expect(result).toContain('highlighted');
    });

    it('should remove dangerous tags', () => {
      const input = '<script>alert("XSS")</script>Hello';
      const result = sanitizeHTML(input);
      expect(result).not.toContain('<script');
      expect(result).not.toContain('alert');
      expect(result).toContain('Hello');
    });

    it('should remove event handlers', () => {
      const input = '<span onclick="alert(1)">Click me</span>';
      const result = sanitizeHTML(input);
      expect(result).not.toContain('onclick');
      expect(result).toContain('Click me');
    });

    it('should remove javascript: URLs', () => {
      const input = '<a href="javascript:alert(1)">Link</a>';
      const result = sanitizeHTML(input);
      expect(result).not.toContain('javascript:');
      expect(result).not.toContain('<a');
    });
  });

  describe('sanitizeUserContent', () => {
    it('should strip all HTML tags', () => {
      const input = '<b>Bold</b> <script>alert(1)</script> text';
      const result = sanitizeUserContent(input);
      expect(result).toBe('Bold  text');
      expect(result).not.toContain('<');
      expect(result).not.toContain('>');
    });

    it('should preserve text content', () => {
      const input = 'Normal text with <fake>tags</fake>';
      const result = sanitizeUserContent(input);
      expect(result).toBe('Normal text with tags');
    });
  });

  describe('escapeHTML', () => {
    it('should escape HTML special characters', () => {
      const input = '<script>alert("XSS")</script>';
      const result = escapeHTML(input);
      expect(result).toBe('&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;');
    });

    it('should escape quotes and apostrophes', () => {
      const input = `"Hello" & 'World'`;
      const result = escapeHTML(input);
      expect(result).toBe('&quot;Hello&quot; &amp; &#039;World&#039;');
    });
  });

  describe('highlightTextSafely', () => {
    it('should highlight search terms safely', () => {
      const text = 'This is a test document';
      const query = 'test';
      const result = highlightTextSafely(text, query);
      expect(result).toContain('<mark class="bg-yellow-200">test</mark>');
      expect(result).toContain('This is a');
      expect(result).toContain('document');
    });

    it('should escape HTML in text before highlighting', () => {
      const text = '<script>alert(1)</script> test document';
      const query = 'test';
      const result = highlightTextSafely(text, query);
      expect(result).not.toContain('<script');
      expect(result).toContain('&lt;script');
      expect(result).toContain('<mark class="bg-yellow-200">test</mark>');
    });

    it('should handle multiple search terms', () => {
      const text = 'The quick brown fox';
      const query = 'quick fox';
      const result = highlightTextSafely(text, query);
      expect(result).toContain('<mark class="bg-yellow-200">quick</mark>');
      expect(result).toContain('<mark class="bg-yellow-200">fox</mark>');
    });

    it('should not highlight terms shorter than 3 characters', () => {
      const text = 'This is a test';
      const query = 'is a';
      const result = highlightTextSafely(text, query);
      expect(result).not.toContain('<mark');
    });

    it('should prevent XSS through search query', () => {
      const text = 'Normal text';
      const query = '<script>alert(1)</script>';
      const result = highlightTextSafely(text, query);
      expect(result).not.toContain('<script');
      expect(result).toBe(escapeHTML(text));
    });
  });

  describe('sanitizeURL', () => {
    it('should allow safe URLs', () => {
      expect(sanitizeURL('https://example.com')).toBe('https://example.com');
      expect(sanitizeURL('http://example.com')).toBe('http://example.com');
      expect(sanitizeURL('/relative/path')).toBe('/relative/path');
      expect(sanitizeURL('#anchor')).toBe('#anchor');
    });

    it('should block javascript: URLs', () => {
      expect(sanitizeURL('javascript:alert(1)')).toBe('');
      expect(sanitizeURL('JAVASCRIPT:alert(1)')).toBe('');
      expect(sanitizeURL(' javascript:alert(1) ')).toBe('');
    });

    it('should block data: URLs', () => {
      expect(sanitizeURL('data:text/html,<script>alert(1)</script>')).toBe('');
      expect(sanitizeURL('DATA:text/html,test')).toBe('');
    });

    it('should block other dangerous protocols', () => {
      expect(sanitizeURL('vbscript:alert(1)')).toBe('');
      expect(sanitizeURL('file:///etc/passwd')).toBe('');
      expect(sanitizeURL('about:blank')).toBe('');
      expect(sanitizeURL('blob:test')).toBe('');
    });

    it('should handle relative URLs', () => {
      const result = sanitizeURL('page.html');
      expect(result).toBe('/page.html');
    });
  });

  describe('sanitizeDataAttribute', () => {
    it('should escape HTML in data attributes', () => {
      const input = '<script>alert(1)</script>';
      const result = sanitizeDataAttribute(input);
      expect(result).toBe('&lt;script&gt;alert(1)&lt;/script&gt;');
    });

    it('should handle null and undefined', () => {
      expect(sanitizeDataAttribute(null)).toBe('');
      expect(sanitizeDataAttribute(undefined)).toBe('');
    });

    it('should convert non-strings to strings', () => {
      expect(sanitizeDataAttribute(123)).toBe('123');
      expect(sanitizeDataAttribute(true)).toBe('true');
      expect(sanitizeDataAttribute({ key: 'value' })).toContain('object');
    });
  });

  describe('sanitizeJSON', () => {
    it('should safely stringify and escape JSON', () => {
      const obj = { key: '<script>alert(1)</script>' };
      const result = sanitizeJSON(obj);
      expect(result).toContain('&lt;script');
      expect(result).not.toContain('<script');
    });

    it('should handle invalid JSON gracefully', () => {
      const circular: any = { a: 1 };
      circular.self = circular;
      const result = sanitizeJSON(circular);
      expect(result).toBe('{}');
    });
  });

  describe('needsSanitization', () => {
    it('should detect HTML tags', () => {
      expect(needsSanitization('<div>test</div>')).toBe(true);
      expect(needsSanitization('normal text')).toBe(false);
    });

    it('should detect special characters', () => {
      expect(needsSanitization('text & more')).toBe(true);
      expect(needsSanitization('text < value')).toBe(true);
      expect(needsSanitization('"quoted"')).toBe(true);
      expect(needsSanitization("'quoted'")).toBe(true);
      expect(needsSanitization('normal text')).toBe(false);
    });
  });

  describe('XSS Attack Vectors', () => {
    it('should prevent IMG tag XSS', () => {
      const attacks = [
        '<img src=x onerror="alert(1)">',
        '<img src="javascript:alert(1)">',
        '<IMG SRC=javascript:alert("XSS")>',
        '<img src=x oneonerrorrror=alert(1)>'
      ];
      
      attacks.forEach(attack => {
        const result = sanitizeHTML(attack);
        expect(result).not.toContain('alert');
        expect(result).not.toContain('<img');
        expect(result).not.toContain('onerror');
      });
    });

    it('should prevent SVG XSS', () => {
      const attack = '<svg onload="alert(1)"><circle r=100></svg>';
      const result = sanitizeHTML(attack);
      expect(result).not.toContain('svg');
      expect(result).not.toContain('onload');
      expect(result).not.toContain('alert');
    });

    it('should prevent style-based XSS', () => {
      const attacks = [
        '<style>body { background: url("javascript:alert(1)") }</style>',
        '<div style="background: url(javascript:alert(1))">test</div>',
        '<div style="expression(alert(1))">test</div>'
      ];
      
      attacks.forEach(attack => {
        const result = sanitizeHTML(attack);
        expect(result).not.toContain('javascript:');
        expect(result).not.toContain('expression');
        expect(result).not.toContain('alert');
      });
    });

    it('should prevent encoded XSS attacks', () => {
      const attacks = [
        '<script>alert(String.fromCharCode(88,83,83))</script>',
        '&#60;script&#62;alert(1)&#60;/script&#62;',
        '<scr\x00ipt>alert(1)</scr\x00ipt>'
      ];
      
      attacks.forEach(attack => {
        const result = sanitizeHTML(attack);
        expect(result).not.toContain('script');
        expect(result).not.toContain('alert');
      });
    });
  });
});
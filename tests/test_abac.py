"""Tests for ABAC engagement scope enforcement"""
import pytest
from app.security.abac import ABACPolicy

def test_engagement_scope_allowed():
    """Test allowed access within engagement scope"""
    user_claims = {
        'engagements': ['eng-001', 'eng-002'],
        'permissions': ['audit_bundle_access'],
        'roles': ['consultant']
    }
    
    assert ABACPolicy.check_engagement_scope(
        user_claims, 'eng-001', 'audit_bundle'
    ) == True

def test_engagement_scope_denied_cross_tenant():
    """Test denied access across engagement boundaries"""
    user_claims = {
        'engagements': ['eng-001'],
        'permissions': ['audit_bundle_access'],
        'roles': ['consultant']
    }
    
    assert ABACPolicy.check_engagement_scope(
        user_claims, 'eng-003', 'audit_bundle'
    ) == False

def test_admin_bypass():
    """Test system admin bypass of engagement checks"""
    user_claims = {
        'engagements': [],
        'roles': ['system_admin']
    }
    
    assert ABACPolicy.check_engagement_scope(
        user_claims, 'eng-any', 'mcp_tools'
    ) == True

def test_missing_permission():
    """Test denied access with missing resource permission"""
    user_claims = {
        'engagements': ['eng-001'],
        'permissions': [],
        'roles': ['viewer']
    }
    
    assert ABACPolicy.check_engagement_scope(
        user_claims, 'eng-001', 'pii_export'
    ) == False
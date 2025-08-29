"""
Tests to verify that security-critical dependencies are at safe versions
"""
import subprocess
import pytest
from typing import Dict, List, Tuple

# Minimum safe versions for vulnerable packages
MINIMUM_SAFE_VERSIONS: Dict[str, str] = {
    'python-multipart': '0.0.9',  # CVE-2024-42671, CVE-2024-37891
    'anyio': '4.4.0',  # CVE-2024-42472
    'pip': '23.3',  # CVE-2023-43804
    'future': '0.18.3',  # CVE-2022-40899
    'wheel': '0.38.1',  # CVE-2022-40898
}

def get_installed_version(package: str) -> str:
    """Get installed version of a package"""
    try:
        result = subprocess.run(
            ['pip3', 'show', package],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                return line.split(':')[1].strip()
    except subprocess.CalledProcessError:
        return None
    return None

def parse_version(version: str) -> List[int]:
    """Parse version string into comparable list of integers"""
    if not version:
        return [0]
    
    try:
        # Handle versions like '0.0.6' or '1.2.3.post1'
        version = version.split('.post')[0]  # Remove post-release
        version = version.split('+')[0]  # Remove local version
        version = version.split('rc')[0]  # Remove release candidate
        version = version.split('b')[0]  # Remove beta
        version = version.split('a')[0]  # Remove alpha
        
        parts = []
        for part in version.split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                # Handle non-numeric parts
                parts.append(0)
        return parts
    except:
        return [0]

def compare_versions(current: str, required: str) -> bool:
    """Check if current version is >= required version"""
    if not current:
        return False
    
    current_parts = parse_version(current)
    required_parts = parse_version(required)
    
    # Pad with zeros to make same length
    max_len = max(len(current_parts), len(required_parts))
    current_parts += [0] * (max_len - len(current_parts))
    required_parts += [0] * (max_len - len(required_parts))
    
    return current_parts >= required_parts

class TestSecurityDependencies:
    """Test suite for security-critical dependency versions"""
    
    def test_python_multipart_version(self):
        """Test that python-multipart is at a safe version (CVE-2024-42671, CVE-2024-37891)"""
        package = 'python-multipart'
        min_version = MINIMUM_SAFE_VERSIONS[package]
        current_version = get_installed_version(package)
        
        if current_version:
            assert compare_versions(current_version, min_version), \
                f"{package} {current_version} is vulnerable. Upgrade to >={min_version} to fix CVE-2024-42671, CVE-2024-37891"
    
    def test_anyio_version(self):
        """Test that anyio is at a safe version (CVE-2024-42472)"""
        package = 'anyio'
        min_version = MINIMUM_SAFE_VERSIONS[package]
        current_version = get_installed_version(package)
        
        if current_version:
            assert compare_versions(current_version, min_version), \
                f"{package} {current_version} is vulnerable. Upgrade to >={min_version} to fix CVE-2024-42472"
    
    def test_pip_version(self):
        """Test that pip is at a safe version (CVE-2023-43804)"""
        package = 'pip'
        min_version = MINIMUM_SAFE_VERSIONS[package]
        current_version = get_installed_version(package)
        
        if current_version:
            assert compare_versions(current_version, min_version), \
                f"{package} {current_version} is vulnerable. Upgrade to >={min_version} to fix CVE-2023-43804"
    
    def test_future_version(self):
        """Test that future is at a safe version (CVE-2022-40899)"""
        package = 'future'
        min_version = MINIMUM_SAFE_VERSIONS[package]
        current_version = get_installed_version(package)
        
        if current_version:
            assert compare_versions(current_version, min_version), \
                f"{package} {current_version} is vulnerable. Upgrade to >={min_version} to fix CVE-2022-40899"
    
    def test_wheel_version(self):
        """Test that wheel is at a safe version (CVE-2022-40898)"""
        package = 'wheel'
        min_version = MINIMUM_SAFE_VERSIONS[package]
        current_version = get_installed_version(package)
        
        if current_version:
            assert compare_versions(current_version, min_version), \
                f"{package} {current_version} is vulnerable. Upgrade to >={min_version} to fix CVE-2022-40898"
    
    def test_all_critical_dependencies(self):
        """Test that all critical dependencies are at safe versions"""
        vulnerabilities = []
        
        for package, min_version in MINIMUM_SAFE_VERSIONS.items():
            current_version = get_installed_version(package)
            if current_version and not compare_versions(current_version, min_version):
                vulnerabilities.append(f"{package} {current_version} -> >={min_version}")
        
        assert not vulnerabilities, \
            f"Found vulnerable packages:\n" + "\n".join(vulnerabilities)

class TestVersionParser:
    """Test suite for version parsing logic"""
    
    def test_parse_simple_version(self):
        """Test parsing simple version strings"""
        assert parse_version('1.2.3') == [1, 2, 3]
        assert parse_version('0.0.6') == [0, 0, 6]
        assert parse_version('10.20.30') == [10, 20, 30]
    
    def test_parse_complex_version(self):
        """Test parsing complex version strings"""
        assert parse_version('1.2.3.post1') == [1, 2, 3]
        assert parse_version('1.2.3rc1') == [1, 2, 3]
        assert parse_version('1.2.3b1') == [1, 2, 3]
        assert parse_version('1.2.3a1') == [1, 2, 3]
        assert parse_version('1.2.3+local') == [1, 2, 3]
    
    def test_compare_versions(self):
        """Test version comparison logic"""
        assert compare_versions('1.2.3', '1.2.2') is True
        assert compare_versions('1.2.3', '1.2.3') is True
        assert compare_versions('1.2.3', '1.2.4') is False
        assert compare_versions('0.0.9', '0.0.6') is True
        assert compare_versions('0.0.6', '0.0.9') is False
        assert compare_versions('4.4.0', '3.7.1') is True
        assert compare_versions('23.3', '21.2.4') is True

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
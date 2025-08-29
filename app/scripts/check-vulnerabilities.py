#!/usr/bin/env python3
"""
Security vulnerability checker for Python dependencies
Checks installed packages against known CVEs
"""
import subprocess
import sys
from typing import Dict, List, Tuple

# Known vulnerabilities with minimum safe versions
KNOWN_VULNERABILITIES: Dict[str, Tuple[str, List[str], str]] = {
    'python-multipart': ('0.0.9', ['CVE-2024-42671', 'CVE-2024-37891'], 'CVSS 6.9-8.1'),
    'anyio': ('4.4.0', ['CVE-2024-42472'], 'CVSS 7.5'),
    'pip': ('23.3', ['CVE-2023-43804'], 'CVSS 7.5'),
    'future': ('0.18.3', ['CVE-2022-40899'], 'CVSS 7.5'),
    'wheel': ('0.38.1', ['CVE-2022-40898'], 'CVSS 7.5'),
    'cryptography': ('42.0.0', ['Various'], 'Security fixes'),
    'urllib3': ('2.2.0', ['Multiple CVEs'], 'Security fixes'),
    'setuptools': ('70.0.0', ['Build security'], 'Security fixes'),
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
    try:
        # Handle versions like '0.0.6' or '1.2.3.post1'
        version = version.split('.post')[0]  # Remove post-release
        version = version.split('+')[0]  # Remove local version
        parts = []
        for part in version.split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                # Handle alpha/beta/rc versions
                parts.append(0)
        return parts
    except:
        return [0]

def compare_versions(current: str, required: str) -> bool:
    """Check if current version is >= required version"""
    current_parts = parse_version(current)
    required_parts = parse_version(required)
    
    # Pad with zeros to make same length
    max_len = max(len(current_parts), len(required_parts))
    current_parts += [0] * (max_len - len(current_parts))
    required_parts += [0] * (max_len - len(required_parts))
    
    return current_parts >= required_parts

def check_vulnerabilities() -> List[Dict]:
    """Check for known vulnerabilities in installed packages"""
    vulnerabilities = []
    
    print("🔍 Checking for known security vulnerabilities...\n")
    
    for package, (min_version, cves, severity) in KNOWN_VULNERABILITIES.items():
        current_version = get_installed_version(package)
        
        if current_version is None:
            print(f"⚪ {package}: Not installed")
            continue
        
        if not compare_versions(current_version, min_version):
            vulnerabilities.append({
                'package': package,
                'current': current_version,
                'required': min_version,
                'cves': cves,
                'severity': severity
            })
            print(f"🔴 {package} {current_version} -> {min_version} ({severity})")
            print(f"   CVEs: {', '.join(cves)}")
        else:
            print(f"✅ {package} {current_version} (secure)")
    
    return vulnerabilities

def generate_fix_commands(vulnerabilities: List[Dict]) -> List[str]:
    """Generate pip commands to fix vulnerabilities"""
    if not vulnerabilities:
        return []
    
    commands = []
    packages = []
    
    for vuln in vulnerabilities:
        packages.append(f"{vuln['package']}>={vuln['required']}")
    
    if packages:
        commands.append(f"pip install --upgrade {' '.join(packages)}")
    
    return commands

def main():
    """Main execution"""
    vulnerabilities = check_vulnerabilities()
    
    print("\n" + "="*60)
    
    if not vulnerabilities:
        print("✅ No known vulnerabilities found!")
        print("All checked packages are at secure versions.")
        return 0
    
    print(f"⚠️  Found {len(vulnerabilities)} vulnerable package(s):\n")
    
    for vuln in vulnerabilities:
        print(f"Package: {vuln['package']}")
        print(f"  Current: {vuln['current']}")
        print(f"  Required: >={vuln['required']}")
        print(f"  Severity: {vuln['severity']}")
        print(f"  CVEs: {', '.join(vuln['cves'])}")
        print()
    
    print("🔧 To fix these vulnerabilities, run:")
    print("-"*40)
    
    commands = generate_fix_commands(vulnerabilities)
    for cmd in commands:
        print(cmd)
    
    print("\nOr use the security requirements file:")
    print("pip install -r requirements-security.txt")
    
    return 1  # Exit with error code

if __name__ == "__main__":
    sys.exit(main())
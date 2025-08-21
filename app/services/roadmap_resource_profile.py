"""Roadmap resource profile service for wave planning and skill mapping"""
import logging
import csv
import io
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict

from app.api.schemas.resource_profile import (
    SkillLevel, RoleType, WavePhase, SkillRequirement, RoleProfile,
    WaveResourceAllocation, InitiativeResourceProfile, ResourcePlanningRequest,
    ResourcePlanningResponse, CSVExportRequest, CSVExportResponse,
    GanttChartRequest, GanttTask, GanttChartResponse, WaveOverlayRequest,
    WaveOverlayResponse, SkillMappingInfo, ResourceConfigurationInfo
)

logger = logging.getLogger(__name__)


class RoadmapResourceProfileService:
    """Service for roadmap resource planning and skill mapping"""
    
    def __init__(self):
        self._skill_catalog = self._initialize_skill_catalog()
        self._role_templates = self._initialize_role_templates()
        self._last_updated = datetime.utcnow()
        self._updated_by = "system"
    
    def _initialize_skill_catalog(self) -> Dict:
        """Initialize comprehensive skill catalog"""
        return {
            "technical_skills": [
                {"name": "Cloud Security Architecture", "category": "technical", "description": "Designing secure cloud solutions"},
                {"name": "Network Security", "category": "technical", "description": "Network security design and implementation"},
                {"name": "Identity and Access Management", "category": "technical", "description": "IAM solutions and governance"},
                {"name": "Vulnerability Assessment", "category": "technical", "description": "Security testing and vulnerability analysis"},
                {"name": "Incident Response", "category": "technical", "description": "Security incident handling and forensics"},
                {"name": "Security Automation", "category": "technical", "description": "Security orchestration and automation"},
                {"name": "Cryptography", "category": "technical", "description": "Cryptographic implementations and key management"},
                {"name": "Azure Security Services", "category": "technical", "description": "Microsoft Azure security solutions"},
                {"name": "Microsoft 365 Security", "category": "technical", "description": "M365 security configuration and management"}
            ],
            "compliance_skills": [
                {"name": "SOC 2 Compliance", "category": "compliance", "description": "SOC 2 Type II auditing and compliance"},
                {"name": "ISO 27001", "category": "compliance", "description": "ISO 27001 implementation and certification"},
                {"name": "NIST Framework", "category": "compliance", "description": "NIST Cybersecurity Framework implementation"},
                {"name": "GDPR Compliance", "category": "compliance", "description": "GDPR privacy and data protection compliance"},
                {"name": "Risk Assessment", "category": "compliance", "description": "Cybersecurity risk assessment and management"},
                {"name": "Audit and Assurance", "category": "compliance", "description": "Internal and external audit processes"},
                {"name": "Policy Development", "category": "compliance", "description": "Security policy and procedure development"}
            ],
            "management_skills": [
                {"name": "Project Management", "category": "management", "description": "Cybersecurity project management"},
                {"name": "Program Management", "category": "management", "description": "Multi-project program coordination"},
                {"name": "Stakeholder Management", "category": "management", "description": "Executive and stakeholder communication"},
                {"name": "Change Management", "category": "management", "description": "Organizational change management"},
                {"name": "Vendor Management", "category": "management", "description": "Security vendor and supplier management"},
                {"name": "Budget Management", "category": "management", "description": "Security budget planning and oversight"},
                {"name": "Team Leadership", "category": "management", "description": "Security team leadership and development"}
            ],
            "analytical_skills": [
                {"name": "Threat Intelligence", "category": "analytical", "description": "Cyber threat intelligence analysis"},
                {"name": "Security Metrics", "category": "analytical", "description": "Security KPI and metrics development"},
                {"name": "Data Analysis", "category": "analytical", "description": "Security data analysis and reporting"},
                {"name": "Business Impact Analysis", "category": "analytical", "description": "Cybersecurity business impact assessment"}
            ]
        }
    
    def _initialize_role_templates(self) -> Dict[RoleType, RoleProfile]:
        """Initialize role templates with default skill requirements"""
        return {
            RoleType.SECURITY_ARCHITECT: RoleProfile(
                role_type=RoleType.SECURITY_ARCHITECT,
                role_title="Senior Security Architect",
                fte_required=1.0,
                duration_weeks=12,
                skill_requirements=[
                    SkillRequirement(skill_name="Cloud Security Architecture", skill_category="technical", 
                                   required_level=SkillLevel.EXPERT, critical=True),
                    SkillRequirement(skill_name="Azure Security Services", skill_category="technical", 
                                   required_level=SkillLevel.ADVANCED, critical=True),
                    SkillRequirement(skill_name="Risk Assessment", skill_category="compliance", 
                                   required_level=SkillLevel.ADVANCED, critical=False)
                ],
                seniority_level="senior",
                remote_eligible=True
            ),
            RoleType.SECURITY_ENGINEER: RoleProfile(
                role_type=RoleType.SECURITY_ENGINEER,
                role_title="Security Engineer",
                fte_required=1.0,
                duration_weeks=8,
                skill_requirements=[
                    SkillRequirement(skill_name="Network Security", skill_category="technical", 
                                   required_level=SkillLevel.ADVANCED, critical=True),
                    SkillRequirement(skill_name="Security Automation", skill_category="technical", 
                                   required_level=SkillLevel.INTERMEDIATE, critical=False),
                    SkillRequirement(skill_name="Incident Response", skill_category="technical", 
                                   required_level=SkillLevel.INTERMEDIATE, critical=False)
                ],
                seniority_level="mid",
                remote_eligible=True
            ),
            RoleType.COMPLIANCE_ANALYST: RoleProfile(
                role_type=RoleType.COMPLIANCE_ANALYST,
                role_title="Compliance Analyst",
                fte_required=0.5,
                duration_weeks=16,
                skill_requirements=[
                    SkillRequirement(skill_name="SOC 2 Compliance", skill_category="compliance", 
                                   required_level=SkillLevel.ADVANCED, critical=True),
                    SkillRequirement(skill_name="ISO 27001", skill_category="compliance", 
                                   required_level=SkillLevel.INTERMEDIATE, critical=False),
                    SkillRequirement(skill_name="Audit and Assurance", skill_category="compliance", 
                                   required_level=SkillLevel.ADVANCED, critical=True)
                ],
                seniority_level="mid",
                remote_eligible=True
            ),
            RoleType.PROJECT_MANAGER: RoleProfile(
                role_type=RoleType.PROJECT_MANAGER,
                role_title="Cybersecurity Project Manager",
                fte_required=0.75,
                duration_weeks=20,
                skill_requirements=[
                    SkillRequirement(skill_name="Project Management", skill_category="management", 
                                   required_level=SkillLevel.EXPERT, critical=True),
                    SkillRequirement(skill_name="Stakeholder Management", skill_category="management", 
                                   required_level=SkillLevel.ADVANCED, critical=True),
                    SkillRequirement(skill_name="Change Management", skill_category="management", 
                                   required_level=SkillLevel.INTERMEDIATE, critical=False)
                ],
                seniority_level="senior",
                remote_eligible=True
            )
        }
    
    def generate_wave_allocations(
        self, 
        initiative_data: Dict, 
        wave_duration_weeks: int = 12,
        start_date: date = None
    ) -> List[WaveResourceAllocation]:
        """Generate wave resource allocations for an initiative"""
        
        if start_date is None:
            start_date = date.today()
        
        total_duration = initiative_data.get('duration_weeks', 24)
        wave_count = max(1, (total_duration + wave_duration_weeks - 1) // wave_duration_weeks)
        
        waves = []
        current_start = start_date
        
        for wave_num in range(1, wave_count + 1):
            wave_end = current_start + timedelta(weeks=min(wave_duration_weeks, 
                                                          total_duration - (wave_num - 1) * wave_duration_weeks))
            
            # Generate role allocations based on initiative complexity and wave
            role_allocations = self._generate_role_allocations_for_wave(
                initiative_data, wave_num, wave_count
            )
            
            wave = WaveResourceAllocation(
                wave=WavePhase(f"wave_{wave_num}"),
                wave_name=f"Wave {wave_num}: {initiative_data.get('name', 'Initiative')}",
                start_date=current_start,
                end_date=wave_end,
                role_allocations=role_allocations,
                critical_path=wave_num <= 2  # First two waves typically critical
            )
            
            # Calculate totals
            wave.total_fte = sum(role.fte_required for role in role_allocations)
            wave.estimated_cost = self._estimate_wave_cost(role_allocations, wave_duration_weeks)
            
            waves.append(wave)
            current_start = wave_end + timedelta(days=1)
        
        return waves
    
    def _generate_role_allocations_for_wave(
        self, 
        initiative_data: Dict, 
        wave_num: int, 
        total_waves: int
    ) -> List[RoleProfile]:
        """Generate role allocations for a specific wave"""
        
        initiative_size = initiative_data.get('t_shirt_size', 'M')
        initiative_type = initiative_data.get('type', 'security_implementation')
        
        # Base role requirements by initiative size
        size_multipliers = {
            'S': 0.5,
            'M': 1.0,
            'L': 1.5,
            'XL': 2.0
        }
        
        multiplier = size_multipliers.get(initiative_size, 1.0)
        
        # Different waves require different role mixes
        if wave_num == 1:  # Planning and architecture wave
            roles = [
                self._create_wave_role(RoleType.SECURITY_ARCHITECT, 1.0 * multiplier, 12),
                self._create_wave_role(RoleType.PROJECT_MANAGER, 0.5 * multiplier, 12),
                self._create_wave_role(RoleType.COMPLIANCE_ANALYST, 0.25 * multiplier, 8)
            ]
        elif wave_num == total_waves:  # Final wave - testing and closure
            roles = [
                self._create_wave_role(RoleType.SECURITY_ENGINEER, 0.75 * multiplier, 8),
                self._create_wave_role(RoleType.PROJECT_MANAGER, 0.5 * multiplier, 8),
                self._create_wave_role(RoleType.COMPLIANCE_ANALYST, 0.5 * multiplier, 12)
            ]
        else:  # Implementation waves
            roles = [
                self._create_wave_role(RoleType.SECURITY_ENGINEER, 1.0 * multiplier, 12),
                self._create_wave_role(RoleType.SECURITY_ARCHITECT, 0.5 * multiplier, 8),
                self._create_wave_role(RoleType.PROJECT_MANAGER, 0.25 * multiplier, 12)
            ]
        
        # Filter out roles with zero FTE
        return [role for role in roles if role.fte_required > 0]
    
    def _create_wave_role(self, role_type: RoleType, fte: float, duration_weeks: int) -> RoleProfile:
        """Create a role profile for a wave with adjusted FTE"""
        template = self._role_templates[role_type]
        
        return RoleProfile(
            role_type=role_type,
            role_title=template.role_title,
            fte_required=round(max(0, min(2.0, fte)), 2),
            duration_weeks=duration_weeks,
            skill_requirements=template.skill_requirements,
            seniority_level=template.seniority_level,
            remote_eligible=template.remote_eligible
        )
    
    def _estimate_wave_cost(self, role_allocations: List[RoleProfile], wave_weeks: int) -> float:
        """Estimate cost for a wave based on role allocations"""
        # Simplified cost estimation based on role types and seniority
        hourly_rates = {
            'junior': 100,
            'mid': 140,
            'senior': 180,
            'principal': 220
        }
        
        total_cost = 0
        for role in role_allocations:
            rate = hourly_rates.get(role.seniority_level, 140)
            hours = role.fte_required * role.duration_weeks * 40  # 40 hours/week
            total_cost += hours * rate
        
        return total_cost
    
    def calculate_resource_profile(self, request: ResourcePlanningRequest) -> ResourcePlanningResponse:
        """Calculate comprehensive resource profile for initiatives"""
        
        initiative_profiles = []
        skill_demand = defaultdict(list)
        wave_overlay = []
        resource_conflicts = []
        
        for initiative_data in request.initiatives:
            # Generate wave allocations
            waves = self.generate_wave_allocations(
                initiative_data,
                request.wave_duration_weeks,
                request.target_start_date
            )
            
            # Calculate skill summary
            skill_summary = self._calculate_skill_summary(waves)
            
            # Create initiative profile
            profile = InitiativeResourceProfile(
                initiative_id=initiative_data.get('initiative_id', ''),
                initiative_name=initiative_data.get('name', ''),
                total_duration_weeks=sum(
                    (wave.end_date - wave.start_date).days // 7 for wave in waves
                ),
                wave_allocations=waves,
                skill_summary=skill_summary,
                total_fte_demand=sum(wave.total_fte or 0 for wave in waves) / len(waves),
                total_estimated_cost=sum(wave.estimated_cost or 0 for wave in waves),
                resource_constraints=self._identify_resource_constraints(waves, request.skill_constraints)
            )
            
            initiative_profiles.append(profile)
            
            # Collect skill demand data
            for wave in waves:
                self._collect_skill_demand(wave, skill_demand)
            
            # Add to wave overlay
            wave_overlay.extend(self._create_wave_overlay_data(waves))
        
        # Identify resource conflicts
        resource_conflicts = self._identify_resource_conflicts(initiative_profiles)
        
        # Generate planning summary
        planning_summary = self._generate_planning_summary(initiative_profiles)
        
        logger.info(
            f"Generated resource profiles for {len(initiative_profiles)} initiatives",
            extra={
                "total_fte_demand": sum(p.total_fte_demand for p in initiative_profiles),
                "total_estimated_cost": sum(p.total_estimated_cost for p in initiative_profiles),
                "planning_horizon_weeks": request.planning_horizon_weeks
            }
        )
        
        return ResourcePlanningResponse(
            initiative_profiles=initiative_profiles,
            planning_summary=planning_summary,
            skill_demand_forecast=dict(skill_demand),
            wave_overlay=wave_overlay,
            resource_conflicts=resource_conflicts
        )
    
    def _calculate_skill_summary(self, waves: List[WaveResourceAllocation]) -> Dict[str, int]:
        """Calculate skill requirements summary"""
        skill_counts = defaultdict(int)
        
        for wave in waves:
            for role in wave.role_allocations:
                for skill in role.skill_requirements:
                    skill_counts[skill.skill_category] += 1
        
        return dict(skill_counts)
    
    def _identify_resource_constraints(
        self, 
        waves: List[WaveResourceAllocation], 
        skill_constraints: Optional[Dict[str, int]]
    ) -> List[str]:
        """Identify potential resource constraints"""
        constraints = []
        
        if skill_constraints:
            for wave in waves:
                for role in wave.role_allocations:
                    role_name = role.role_type.value
                    if role_name in skill_constraints:
                        if role.fte_required > skill_constraints[role_name]:
                            constraints.append(
                                f"Insufficient {role_name} capacity in {wave.wave_name}"
                            )
        
        return constraints
    
    def _collect_skill_demand(self, wave: WaveResourceAllocation, skill_demand: Dict):
        """Collect skill demand data for forecasting"""
        period_key = f"{wave.start_date.strftime('%Y-%m')}"
        
        if period_key not in skill_demand:
            skill_demand[period_key] = []
        
        for role in wave.role_allocations:
            for skill in role.skill_requirements:
                skill_demand[period_key].append({
                    "skill_name": skill.skill_name,
                    "skill_category": skill.skill_category,
                    "required_level": skill.required_level.value,
                    "fte_demand": role.fte_required,
                    "critical": skill.critical
                })
    
    def _create_wave_overlay_data(self, waves: List[WaveResourceAllocation]) -> List[Dict]:
        """Create wave overlay data for visualization"""
        overlay_data = []
        
        for wave in waves:
            overlay_data.append({
                "wave_id": wave.wave.value,
                "wave_name": wave.wave_name,
                "start_date": wave.start_date.isoformat(),
                "end_date": wave.end_date.isoformat(),
                "total_fte": wave.total_fte,
                "estimated_cost": wave.estimated_cost,
                "critical_path": wave.critical_path,
                "role_count": len(wave.role_allocations)
            })
        
        return overlay_data
    
    def _identify_resource_conflicts(
        self, 
        profiles: List[InitiativeResourceProfile]
    ) -> List[Dict]:
        """Identify resource conflicts between initiatives"""
        conflicts = []
        
        # Group overlapping waves by time period
        time_periods = defaultdict(list)
        
        for profile in profiles:
            for wave in profile.wave_allocations:
                period_key = f"{wave.start_date}-{wave.end_date}"
                time_periods[period_key].append({
                    "initiative": profile.initiative_name,
                    "wave": wave,
                    "fte_demand": wave.total_fte
                })
        
        # Identify periods with high resource demand
        for period, wave_data in time_periods.items():
            if len(wave_data) > 1:
                total_fte = sum(w["fte_demand"] or 0 for w in wave_data)
                if total_fte > 5.0:  # Threshold for potential conflict
                    conflicts.append({
                        "period": period,
                        "conflict_type": "high_resource_demand",
                        "total_fte_demand": total_fte,
                        "affected_initiatives": [w["initiative"] for w in wave_data],
                        "recommendation": "Consider staggering initiatives or increasing team capacity"
                    })
        
        return conflicts
    
    def _generate_planning_summary(self, profiles: List[InitiativeResourceProfile]) -> Dict:
        """Generate overall planning summary"""
        total_initiatives = len(profiles)
        total_fte_demand = sum(p.total_fte_demand for p in profiles)
        total_cost = sum(p.total_estimated_cost for p in profiles)
        
        # Skill category distribution
        skill_distribution = defaultdict(int)
        for profile in profiles:
            for category, count in profile.skill_summary.items():
                skill_distribution[category] += count
        
        return {
            "total_initiatives": total_initiatives,
            "total_fte_demand": round(total_fte_demand, 2),
            "total_estimated_cost": total_cost,
            "average_initiative_cost": total_cost / total_initiatives if total_initiatives > 0 else 0,
            "skill_category_distribution": dict(skill_distribution),
            "planning_metrics": {
                "peak_fte_demand": max(p.total_fte_demand for p in profiles) if profiles else 0,
                "longest_initiative_weeks": max(p.total_duration_weeks for p in profiles) if profiles else 0,
                "most_constrained_initiative": max(
                    profiles, 
                    key=lambda p: len(p.resource_constraints)
                ).initiative_name if profiles else None
            }
        }
    
    def export_to_csv(self, profiles: List[InitiativeResourceProfile], request: CSVExportRequest) -> CSVExportResponse:
        """Export resource planning data to CSV format"""
        
        output = io.StringIO()
        
        if request.export_format == "summary":
            writer = csv.writer(output)
            writer.writerow([
                "Initiative ID", "Initiative Name", "Total Duration (Weeks)", 
                "Total FTE Demand", "Total Estimated Cost", "Wave Count", "Resource Constraints"
            ])
            
            for profile in profiles:
                if not request.initiative_ids or profile.initiative_id in request.initiative_ids:
                    writer.writerow([
                        profile.initiative_id,
                        profile.initiative_name,
                        profile.total_duration_weeks,
                        profile.total_fte_demand,
                        profile.total_estimated_cost,
                        len(profile.wave_allocations),
                        "; ".join(profile.resource_constraints)
                    ])
        
        elif request.export_format == "detailed":
            writer = csv.writer(output)
            headers = [
                "Initiative ID", "Initiative Name", "Wave", "Wave Name", 
                "Start Date", "End Date", "Role Type", "Role Title", "FTE Required", 
                "Duration Weeks", "Seniority Level"
            ]
            
            if request.include_skills:
                headers.extend(["Skills Required", "Critical Skills"])
            
            if request.include_costs:
                headers.extend(["Wave Cost", "Hourly Rate Range"])
            
            writer.writerow(headers)
            
            for profile in profiles:
                if not request.initiative_ids or profile.initiative_id in request.initiative_ids:
                    for wave in profile.wave_allocations:
                        for role in wave.role_allocations:
                            row = [
                                profile.initiative_id,
                                profile.initiative_name,
                                wave.wave.value,
                                wave.wave_name,
                                wave.start_date.isoformat(),
                                wave.end_date.isoformat(),
                                role.role_type.value,
                                role.role_title,
                                role.fte_required,
                                role.duration_weeks,
                                role.seniority_level
                            ]
                            
                            if request.include_skills:
                                skills = [s.skill_name for s in role.skill_requirements]
                                critical_skills = [s.skill_name for s in role.skill_requirements if s.critical]
                                row.extend(["; ".join(skills), "; ".join(critical_skills)])
                            
                            if request.include_costs:
                                row.extend([wave.estimated_cost, str(role.hourly_rate_range or {})])
                            
                            writer.writerow(row)
        
        elif request.export_format == "skills_matrix":
            writer = csv.writer(output)
            
            # Collect all unique skills
            all_skills = set()
            for profile in profiles:
                for wave in profile.wave_allocations:
                    for role in wave.role_allocations:
                        for skill in role.skill_requirements:
                            all_skills.add(skill.skill_name)
            
            headers = ["Initiative ID", "Role Type"] + sorted(list(all_skills))
            writer.writerow(headers)
            
            for profile in profiles:
                if not request.initiative_ids or profile.initiative_id in request.initiative_ids:
                    for wave in profile.wave_allocations:
                        for role in wave.role_allocations:
                            row = [profile.initiative_id, role.role_type.value]
                            
                            role_skills = {s.skill_name: s.required_level.value for s in role.skill_requirements}
                            for skill in sorted(list(all_skills)):
                                row.append(role_skills.get(skill, ""))
                            
                            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        record_count = len(csv_content.split('\n')) - 1  # Subtract header row
        filename = f"resource_planning_{request.export_format}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logger.info(
            f"Exported resource planning data to CSV",
            extra={
                "export_format": request.export_format,
                "record_count": record_count,
                "include_skills": request.include_skills,
                "include_costs": request.include_costs
            }
        )
        
        return CSVExportResponse(
            csv_content=csv_content,
            filename=filename,
            record_count=record_count,
            export_format=request.export_format
        )
    
    def generate_gantt_chart_data(
        self, 
        profiles: List[InitiativeResourceProfile], 
        request: GanttChartRequest
    ) -> GanttChartResponse:
        """Generate Gantt chart data for resource planning"""
        
        tasks = []
        milestone_dates = []
        all_start_dates = []
        all_end_dates = []
        
        for profile in profiles:
            if not request.initiative_ids or profile.initiative_id in request.initiative_ids:
                
                # Add initiative-level task
                initiative_start = min(wave.start_date for wave in profile.wave_allocations)
                initiative_end = max(wave.end_date for wave in profile.wave_allocations)
                
                all_start_dates.append(initiative_start)
                all_end_dates.append(initiative_end)
                
                initiative_task = GanttTask(
                    task_id=f"init_{profile.initiative_id}",
                    task_name=profile.initiative_name,
                    start_date=initiative_start,
                    end_date=initiative_end,
                    duration_days=(initiative_end - initiative_start).days,
                    initiative_id=profile.initiative_id,
                    wave=WavePhase.WAVE_1,  # Parent task
                    resource_allocation=[],
                    critical_path=any(wave.critical_path for wave in profile.wave_allocations)
                )
                tasks.append(initiative_task)
                
                # Add wave-level tasks
                for wave in profile.wave_allocations:
                    wave_task = GanttTask(
                        task_id=f"wave_{profile.initiative_id}_{wave.wave.value}",
                        task_name=wave.wave_name,
                        start_date=wave.start_date,
                        end_date=wave.end_date,
                        duration_days=(wave.end_date - wave.start_date).days,
                        parent_id=initiative_task.task_id,
                        initiative_id=profile.initiative_id,
                        wave=wave.wave,
                        resource_allocation=[
                            {
                                "role_type": role.role_type.value,
                                "fte_required": role.fte_required,
                                "duration_weeks": role.duration_weeks
                            }
                            for role in wave.role_allocations
                        ],
                        critical_path=wave.critical_path
                    )
                    tasks.append(wave_task)
                    
                    # Add milestone for wave completion
                    milestone_dates.append({
                        "date": wave.end_date.isoformat(),
                        "name": f"{wave.wave_name} Complete",
                        "initiative_id": profile.initiative_id,
                        "type": "wave_completion"
                    })
        
        # Calculate timeline bounds
        timeline_start = min(all_start_dates) if all_start_dates else date.today()
        timeline_end = max(all_end_dates) if all_end_dates else date.today()
        
        # Generate resource summary
        resource_summary = self._generate_gantt_resource_summary(tasks)
        
        # Generate skill heatmap if requested
        skill_heatmap = None
        if request.include_skill_heatmap:
            skill_heatmap = self._generate_skill_heatmap(profiles, timeline_start, timeline_end)
        
        # Identify critical path
        critical_path = [task.task_id for task in tasks if task.critical_path]
        
        logger.info(
            f"Generated Gantt chart data",
            extra={
                "task_count": len(tasks),
                "timeline_days": (timeline_end - timeline_start).days,
                "milestone_count": len(milestone_dates),
                "include_resource_overlay": request.include_resource_overlay
            }
        )
        
        return GanttChartResponse(
            tasks=tasks,
            timeline_start=timeline_start,
            timeline_end=timeline_end,
            resource_summary=resource_summary,
            skill_heatmap=skill_heatmap,
            critical_path=critical_path,
            milestone_dates=milestone_dates
        )
    
    def _generate_gantt_resource_summary(self, tasks: List[GanttTask]) -> Dict:
        """Generate resource utilization summary for Gantt chart"""
        role_utilization = defaultdict(float)
        wave_utilization = defaultdict(float)
        
        for task in tasks:
            if task.resource_allocation:
                for resource in task.resource_allocation:
                    role_utilization[resource["role_type"]] += resource["fte_required"]
                    wave_utilization[task.wave.value] += resource["fte_required"]
        
        return {
            "total_tasks": len(tasks),
            "role_utilization": dict(role_utilization),
            "wave_utilization": dict(wave_utilization),
            "peak_fte_demand": max(role_utilization.values()) if role_utilization else 0
        }
    
    def _generate_skill_heatmap(
        self, 
        profiles: List[InitiativeResourceProfile], 
        start_date: date, 
        end_date: date
    ) -> Dict:
        """Generate skill demand heatmap data"""
        # Create monthly periods
        current_date = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        periods = []
        
        while current_date <= end_month:
            periods.append(current_date.strftime("%Y-%m"))
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        # Calculate skill demand by period
        skill_demand = defaultdict(lambda: defaultdict(float))
        
        for profile in profiles:
            for wave in profile.wave_allocations:
                wave_month = wave.start_date.strftime("%Y-%m")
                if wave_month in periods:
                    for role in wave.role_allocations:
                        for skill in role.skill_requirements:
                            skill_demand[skill.skill_category][wave_month] += role.fte_required
        
        return {
            "periods": periods,
            "skill_demand": {category: dict(demands) for category, demands in skill_demand.items()},
            "max_demand": max(
                max(demands.values()) if demands else 0 
                for demands in skill_demand.values()
            ) if skill_demand else 0
        }
    
    def generate_wave_overlay(self, request: WaveOverlayRequest) -> WaveOverlayResponse:
        """Generate wave overlay visualization data"""
        
        # Generate standard wave periods
        wave_periods = []
        current_date = date.today()
        
        for i in range(5):  # 5 waves
            wave_start = current_date + timedelta(weeks=i * 12)
            wave_end = wave_start + timedelta(weeks=12)
            
            wave_periods.append({
                "wave": f"wave_{i+1}",
                "wave_name": f"Wave {i+1}",
                "start_date": wave_start.isoformat(),
                "end_date": wave_end.isoformat(),
                "duration_weeks": 12
            })
        
        # Generate sample resource utilization
        resource_utilization = {
            "wave_1": {"total_fte": 8.5, "roles": {"security_architect": 2, "security_engineer": 3, "project_manager": 1.5}},
            "wave_2": {"total_fte": 12.0, "roles": {"security_engineer": 4, "compliance_analyst": 2, "project_manager": 2}},
            "wave_3": {"total_fte": 10.5, "roles": {"security_engineer": 3.5, "security_architect": 1.5, "project_manager": 1.5}},
            "wave_4": {"total_fte": 7.0, "roles": {"compliance_analyst": 2.5, "security_engineer": 2, "project_manager": 1}},
            "wave_5": {"total_fte": 5.5, "roles": {"security_engineer": 2, "compliance_analyst": 1.5, "project_manager": 0.75}}
        }
        
        # Generate skill demand trends
        skill_demand_trends = {
            "technical": [8, 12, 10, 6, 4],
            "compliance": [3, 6, 5, 8, 6],
            "management": [5, 6, 5, 4, 3]
        }
        
        # Generate cost distribution
        cost_distribution = {
            "wave_1": 450000,
            "wave_2": 680000,
            "wave_3": 580000,
            "wave_4": 420000,
            "wave_5": 320000
        }
        
        # Capacity analysis
        capacity_analysis = {
            "current_capacity": {"total_fte": 15.0, "utilization_rate": 0.75},
            "demand_vs_capacity": [
                {"wave": "wave_1", "demand": 8.5, "capacity": 15.0, "utilization": 0.57},
                {"wave": "wave_2", "demand": 12.0, "capacity": 15.0, "utilization": 0.80},
                {"wave": "wave_3", "demand": 10.5, "capacity": 15.0, "utilization": 0.70},
                {"wave": "wave_4", "demand": 7.0, "capacity": 15.0, "utilization": 0.47},
                {"wave": "wave_5", "demand": 5.5, "capacity": 15.0, "utilization": 0.37}
            ]
        }
        
        # Generate recommendations
        recommendations = [
            "Wave 2 shows peak resource demand - consider augmenting team capacity",
            "Compliance skills are most constrained in Wave 4 - plan early hiring",
            "Wave 5 has low utilization - opportunity for new initiative starts",
            "Security engineer demand is consistent - maintain steady staffing",
            "Consider cross-training to improve resource flexibility"
        ]
        
        logger.info(
            f"Generated wave overlay visualization",
            extra={
                "wave_count": len(wave_periods),
                "planning_horizon_weeks": request.planning_horizon_weeks,
                "aggregate_by": request.aggregate_by
            }
        )
        
        return WaveOverlayResponse(
            wave_periods=wave_periods,
            resource_utilization=resource_utilization,
            skill_demand_trends=skill_demand_trends,
            cost_distribution=cost_distribution,
            capacity_analysis=capacity_analysis,
            recommendations=recommendations
        )
    
    def get_configuration_info(self) -> ResourceConfigurationInfo:
        """Get resource planning configuration information"""
        
        available_roles = [
            {
                "role_type": role_type.value,
                "description": template.role_title,
                "typical_fte": template.fte_required,
                "typical_duration": template.duration_weeks,
                "seniority_level": template.seniority_level
            }
            for role_type, template in self._role_templates.items()
        ]
        
        skill_mapping = SkillMappingInfo(
            available_skills=sum(self._skill_catalog.values(), []),
            skill_categories=list(self._skill_catalog.keys()),
            role_skill_matrix={
                role_type: [skill.skill_name for skill in template.skill_requirements]
                for role_type, template in self._role_templates.items()
            },
            proficiency_definitions={
                SkillLevel.BEGINNER: "Basic understanding with guidance needed",
                SkillLevel.INTERMEDIATE: "Solid working knowledge with minimal guidance",
                SkillLevel.ADVANCED: "Deep expertise with ability to guide others",
                SkillLevel.EXPERT: "Industry-leading expertise and thought leadership"
            }
        )
        
        return ResourceConfigurationInfo(
            available_roles=available_roles,
            skill_mapping=skill_mapping,
            default_wave_duration=12,
            max_planning_horizon=156,  # 3 years
            supported_export_formats=["summary", "detailed", "skills_matrix"],
            gantt_granularities=["weekly", "monthly", "quarterly"]
        )


# Global service instance
roadmap_resource_service = RoadmapResourceProfileService()
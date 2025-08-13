"use client";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

interface ScoreRadarProps {
  scores: {
    pillar_id: string;
    pillar_name: string;
    score: number | null;
  }[];
}

export default function ScoreRadar({ scores }: ScoreRadarProps) {
  // Transform data for radar chart
  const data = scores.map(item => ({
    pillar: item.pillar_name,
    score: item.score || 0,
    fullMark: 5
  }));

  return (
    <div className="w-full h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data}>
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis 
            dataKey="pillar" 
            tick={{ fontSize: 12 }}
            className="text-gray-600"
          />
          <PolarRadiusAxis 
            angle={90} 
            domain={[0, 5]} 
            tickCount={6}
            tick={{ fontSize: 10 }}
          />
          <Radar 
            name="Current Score" 
            dataKey="score" 
            stroke="#3b82f6" 
            fill="#3b82f6" 
            fillOpacity={0.4}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}











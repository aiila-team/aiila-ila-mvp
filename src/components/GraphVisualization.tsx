import React, { useEffect, useRef, useState } from 'react';
import { GraphData, GraphNode } from '../types';

interface GraphVisualizationProps {
  data: GraphData | null;
  onNodeClick?: (node: GraphNode) => void;
  height?: number;
}

const NODE_RADIUS = 22;

const riskColor = (score?: number): string => {
  if (!score) return '#64748b';
  if (score >= 80) return '#ef4444';
  if (score >= 60) return '#f97316';
  if (score >= 40) return '#eab308';
  return '#3b82f6';
};

const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  data,
  onNodeClick,
  height = 500,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  useEffect(() => {
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height,
        });
      }
    });
    if (svgRef.current?.parentElement) {
      observer.observe(svgRef.current.parentElement);
    }
    return () => observer.disconnect();
  }, [height]);

  if (!data || data.nodes.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-slate-900 rounded-xl text-gray-500 text-sm"
        style={{ height }}
      >
        No graph data available
      </div>
    );
  }

  // Simple circular layout if no positions provided
  const layoutNodes = data.nodes.map((node, i) => {
    if (node.x !== undefined && node.y !== undefined) return node;
    const angle = (i / data.nodes.length) * 2 * Math.PI;
    const r = Math.min(dimensions.width, dimensions.height) * 0.35;
    return {
      ...node,
      x: dimensions.width / 2 + r * Math.cos(angle),
      y: dimensions.height / 2 + r * Math.sin(angle),
    };
  });

  const nodeMap = Object.fromEntries(layoutNodes.map((n) => [n.id, n]));

  return (
    <div className="relative w-full bg-slate-900 rounded-xl overflow-hidden border border-slate-700">
      <svg
        ref={svgRef}
        width="100%"
        height={height}
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="10"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
          </marker>
        </defs>

        {/* Edges */}
        {data.edges.map((edge) => {
          const src = nodeMap[edge.source];
          const tgt = nodeMap[edge.target];
          if (!src || !tgt) return null;
          return (
            <g key={edge.id}>
              <line
                x1={src.x}
                y1={src.y}
                x2={tgt.x}
                y2={tgt.y}
                stroke="#334155"
                strokeWidth={2}
                markerEnd="url(#arrow)"
              />
              {edge.label && (
                <text
                  x={((src.x ?? 0) + (tgt.x ?? 0)) / 2}
                  y={((src.y ?? 0) + (tgt.y ?? 0)) / 2 - 4}
                  fill="#64748b"
                  fontSize="10"
                  textAnchor="middle"
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {layoutNodes.map((node) => (
          <g
            key={node.id}
            transform={`translate(${node.x}, ${node.y})`}
            onClick={() => onNodeClick?.(node)}
            onMouseEnter={() => setHoveredNode(node.id)}
            onMouseLeave={() => setHoveredNode(null)}
            style={{ cursor: 'pointer' }}
          >
            <circle
              r={hoveredNode === node.id ? NODE_RADIUS + 3 : NODE_RADIUS}
              fill={riskColor(node.risk_score)}
              fillOpacity={0.2}
              stroke={riskColor(node.risk_score)}
              strokeWidth={2}
              style={{ transition: 'r 0.15s ease' }}
            />
            <text
              textAnchor="middle"
              dominantBaseline="middle"
              fill="white"
              fontSize="10"
              fontWeight="600"
            >
              {node.label.length > 10 ? node.label.slice(0, 9) + '…' : node.label}
            </text>
            {hoveredNode === node.id && (
              <text
                textAnchor="middle"
                dominantBaseline="middle"
                y={NODE_RADIUS + 14}
                fill="#94a3b8"
                fontSize="9"
              >
                {node.type}
              </text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
};

export default GraphVisualization;

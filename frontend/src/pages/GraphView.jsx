import { useState, useEffect, useRef } from 'react';
import TopNav from '../components/TopNav.jsx';
import { MOCK_GRAPH } from '../mockData.js';
import { getEntityColor } from '../utils.js';
import { RiskScoreBadge } from '../components/RiskScore.jsx';

function GraphCanvas({ nodes, edges, selectedNode, onNodeClick, hops }) {
  const canvasRef = useRef(null);
  const posRef = useRef({});
  const animRef = useRef(null);

  // Initialize positions in a circle
  useEffect(() => {
    const visNodes = getVisibleNodes(nodes, edges, hops);
    const cx = 400, cy = 280, r = 200;
    visNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / visNodes.length - Math.PI / 2;
      posRef.current[node.id] = posRef.current[node.id] || {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
        vx: 0, vy: 0,
      };
    });
    // Remove hidden nodes
    Object.keys(posRef.current).forEach(id => {
      if (!visNodes.find(n => n.id === id)) delete posRef.current[id];
    });
  }, [nodes, hops]);

  function getVisibleNodes(nodes, edges, hops) {
    if (hops >= 3) return nodes;
    // Simple BFS from first node
    const root = nodes[0]?.id;
    if (!root) return nodes;
    const visited = new Set([root]);
    let frontier = [root];
    for (let h = 0; h < hops; h++) {
      const next = [];
      frontier.forEach(id => {
        edges.forEach(e => {
          if (e.source === id && !visited.has(e.target)) { visited.add(e.target); next.push(e.target); }
          if (e.target === id && !visited.has(e.source)) { visited.add(e.source); next.push(e.source); }
        });
      });
      frontier = next;
    }
    return nodes.filter(n => visited.has(n.id));
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    function draw() {
      ctx.clearRect(0, 0, 800, 560);

      // Background grid
      ctx.strokeStyle = 'rgba(255,255,255,0.025)';
      ctx.lineWidth = 0.5;
      for (let x = 0; x < 800; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 560); ctx.stroke(); }
      for (let y = 0; y < 560; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(800, y); ctx.stroke(); }

      const visNodes = getVisibleNodes(nodes, edges, hops);
      const visIds = new Set(visNodes.map(n => n.id));
      const visEdges = edges.filter(e => visIds.has(e.source) && visIds.has(e.target));

      // Simple force simulation step
      const positions = posRef.current;
      visNodes.forEach(n => {
        const pos = positions[n.id];
        if (!pos) return;
        // Repulsion
        visNodes.forEach(m => {
          if (m.id === n.id) return;
          const mp = positions[m.id];
          if (!mp) return;
          const dx = pos.x - mp.x, dy = pos.y - mp.y;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = 3000 / (dist * dist);
          pos.vx += (dx / dist) * force * 0.01;
          pos.vy += (dy / dist) * force * 0.01;
        });
        // Center gravity
        pos.vx += (400 - pos.x) * 0.0005;
        pos.vy += (280 - pos.y) * 0.0005;
        // Edge attraction
        visEdges.forEach(e => {
          const otherId = e.source === n.id ? e.target : e.source === n.id ? e.target : null;
          if (!otherId || e.source !== n.id && e.target !== n.id) return;
          const other = positions[otherId];
          if (!other) return;
          const dx = other.x - pos.x, dy = other.y - pos.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          pos.vx += dx * 0.002;
          pos.vy += dy * 0.002;
        });
        // Dampen + move
        pos.vx *= 0.85; pos.vy *= 0.85;
        pos.x = Math.max(50, Math.min(750, pos.x + pos.vx));
        pos.y = Math.max(50, Math.min(510, pos.y + pos.vy));
      });

      // Draw edges
      visEdges.forEach(e => {
        const sp = positions[e.source], tp = positions[e.target];
        if (!sp || !tp) return;
        ctx.beginPath();
        ctx.moveTo(sp.x, sp.y);
        ctx.lineTo(tp.x, tp.y);
        ctx.strokeStyle = 'rgba(255,255,255,0.08)';
        ctx.lineWidth = 1;
        ctx.stroke();
        // Relation label
        const mx = (sp.x + tp.x) / 2, my = (sp.y + tp.y) / 2;
        ctx.fillStyle = 'rgba(107,114,128,0.8)';
        ctx.font = '9px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        ctx.fillText(e.relation, mx, my - 4);
      });

      // Draw nodes
      visNodes.forEach(n => {
        const pos = positions[n.id];
        if (!pos) return;
        const color = getEntityColor(n.type);
        const isSelected = selectedNode?.id === n.id;
        const r = isSelected ? 14 : 11;

        // Glow for selected
        if (isSelected) {
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, r + 8, 0, Math.PI * 2);
          ctx.fillStyle = color + '20';
          ctx.fill();
        }

        // Node circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color + '25';
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = isSelected ? 2.5 : 1.5;
        ctx.stroke();

        // Label
        ctx.fillStyle = '#D1D5DB';
        ctx.font = `${isSelected ? 10 : 9}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        const label = n.label.length > 16 ? n.label.slice(0, 14) + '…' : n.label;
        ctx.fillText(label, pos.x, pos.y + r + 12);

        // Type
        ctx.fillStyle = color + 'AA';
        ctx.font = '8px JetBrains Mono, monospace';
        ctx.fillText(n.type, pos.x, pos.y + r + 22);
      });

      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [nodes, edges, selectedNode, hops]);

  const handleClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = 800 / rect.width;
    const scaleY = 560 / rect.height;
    const mx = (e.clientX - rect.left) * scaleX;
    const my = (e.clientY - rect.top) * scaleY;
    const positions = posRef.current;
    for (const node of nodes) {
      const pos = positions[node.id];
      if (!pos) continue;
      const dx = mx - pos.x, dy = my - pos.y;
      if (Math.sqrt(dx * dx + dy * dy) < 18) { onNodeClick(node); return; }
    }
    onNodeClick(null);
  };

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={560}
      onClick={handleClick}
      style={{
        width: '100%',
        height: '100%',
        cursor: 'crosshair',
        display: 'block',
      }}
    />
  );
}

export default function GraphView() {
  const [selectedNode, setSelectedNode] = useState(null);
  const [hops, setHops] = useState(2);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopNav title="Graph View" subtitle={`${MOCK_GRAPH.nodes.length} NODES · ${MOCK_GRAPH.edges.length} EDGES`} />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Graph canvas */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden', background: '#0A0C10' }}>
          {/* Controls */}
          <div style={{
            position: 'absolute',
            top: '12px',
            left: '12px',
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(13,15,20,0.9)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '8px',
            padding: '8px 12px',
          }}>
            <span style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginRight: '4px' }}>DEPTH</span>
            {[1, 2, 3].map(h => (
              <button
                key={h}
                onClick={() => setHops(h)}
                style={{
                  width: '28px', height: '28px',
                  borderRadius: '5px',
                  border: `1px solid ${hops === h ? 'rgba(245,158,11,0.5)' : 'rgba(255,255,255,0.08)'}`,
                  background: hops === h ? 'rgba(245,158,11,0.12)' : 'transparent',
                  color: hops === h ? '#F59E0B' : '#6B7280',
                  fontSize: '12px',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >{h}</button>
            ))}
          </div>

          {/* Legend */}
          <div style={{
            position: 'absolute',
            bottom: '12px',
            left: '12px',
            background: 'rgba(13,15,20,0.9)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '8px',
            padding: '10px 14px',
          }}>
            {[
              { type: 'Person', color: '#60A5FA' },
              { type: 'Phone', color: '#34D399' },
              { type: 'SocialAccount', color: '#F59E0B' },
              { type: 'UPIAccount', color: '#A78BFA' },
            ].map(item => (
              <div key={item.type} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: item.color, boxShadow: `0 0 4px ${item.color}` }} />
                <span style={{ fontSize: '10px', color: '#6B7280', fontFamily: 'JetBrains Mono, monospace' }}>{item.type}</span>
              </div>
            ))}
          </div>

          <GraphCanvas
            nodes={MOCK_GRAPH.nodes}
            edges={MOCK_GRAPH.edges}
            selectedNode={selectedNode}
            onNodeClick={setSelectedNode}
            hops={hops}
          />
        </div>

        {/* Node detail panel */}
        <div style={{
          width: '260px',
          borderLeft: '1px solid rgba(255,255,255,0.06)',
          background: '#0D0F14',
          padding: '16px',
          overflowY: 'auto',
        }}>
          {selectedNode ? (
            <div className="animate-slide-right">
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '600', fontSize: '15px', color: '#F1F5F9', marginBottom: '4px' }}>
                  {selectedNode.label}
                </div>
                <div style={{ fontSize: '10px', color: getEntityColor(selectedNode.type), fontFamily: 'JetBrains Mono, monospace' }}>
                  {selectedNode.type.toUpperCase()}
                </div>
              </div>
              <RiskScoreBadge score={selectedNode.risk} size="md" />
              <div style={{ marginTop: '16px' }}>
                <div style={{ fontSize: '10px', color: '#374151', fontFamily: 'JetBrains Mono, monospace', marginBottom: '8px' }}>
                  CONNECTIONS
                </div>
                {MOCK_GRAPH.edges
                  .filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
                  .map((edge, i) => {
                    const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                    const other = MOCK_GRAPH.nodes.find(n => n.id === otherId);
                    if (!other) return null;
                    return (
                      <div key={i} style={{
                        padding: '7px 10px',
                        background: 'rgba(255,255,255,0.03)',
                        borderRadius: '6px',
                        marginBottom: '4px',
                        cursor: 'pointer',
                      }} onClick={() => setSelectedNode(other)}>
                        <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginBottom: '2px' }}>
                          {edge.relation}
                        </div>
                        <div style={{ fontSize: '12px', color: getEntityColor(other.type) }}>
                          {other.label}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '200px', gap: '8px' }}>
              <div style={{ fontSize: '24px', opacity: 0.2 }}>⬡</div>
              <div style={{ fontSize: '11px', color: '#374151', fontFamily: 'Inter, sans-serif', textAlign: 'center' }}>
                Click a node to view details
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

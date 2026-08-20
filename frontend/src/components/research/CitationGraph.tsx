import { useState, useMemo, useCallback, useRef } from 'react';
import {
  Network,
  Table as TableIcon,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from 'lucide-react';
import { PaperCard } from './PaperCard';
import { LiteratureMatrix } from './LiteratureMatrix';
import type { PaperNode, CitationEdge } from './types';

const INITIAL_PAPERS: PaperNode[] = [
  {
    id: 'paper-vaswani2017',
    title: 'Attention Is All You Need',
    authors: ['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar', 'Jakob Uszkoreit'],
    year: 2017,
    venue: 'NeurIPS 2017',
    citations: 124000,
    cluster: 'Architecture',
    abstract:
      'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.',
    claims: [
      'Self-attention reduces sequential computation from O(n) to O(1) depth.',
      'Achieves 28.4 BLEU on WMT 2014 English-to-German translation.',
    ],
    methodology: 'Multi-Head Scaled Dot-Product Attention without recurrence.',
    dataset: 'WMT 2014 En-De',
    metric: '28.4 BLEU',
    baseline: 'ByteNet, ConvS2S',
    gap: 'Quadratic O(N^2) memory complexity with sequence length.',
    x: 400,
    y: 280,
  },
  {
    id: 'paper-devlin2018',
    title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
    authors: ['Jacob Devlin', 'Ming-Wei Chang', 'Kenton Lee', 'Kristina Toutanova'],
    year: 2018,
    venue: 'NAACL 2019',
    citations: 88000,
    cluster: 'Theoretical Analysis',
    abstract:
      'We introduce BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations.',
    claims: [
      'Masked Language Modeling (MLM) allows bidirectional contextual conditioning.',
      'SOTA on 11 NLP tasks including GLUE benchmark.',
    ],
    methodology: 'Masked Language Modeling + Next Sentence Prediction on Transformer Encoders.',
    dataset: 'GLUE Benchmark',
    metric: '80.5 Average',
    baseline: 'OpenAI GPT (autoregressive)',
    gap: 'Cannot easily generate long continuous text sequentially.',
    x: 220,
    y: 160,
  },
  {
    id: 'paper-brown2020',
    title: 'Language Models are Few-Shot Learners (GPT-3)',
    authors: ['Tom Brown', 'Benjamin Mann', 'Nick Ryder', 'Dario Amodei'],
    year: 2020,
    venue: 'NeurIPS 2020',
    citations: 45000,
    cluster: 'Architecture',
    abstract:
      'We demonstrate that scaling up language models greatly improves task-agnostic, few-shot performance, sometimes even reaching competitiveness with prior state-of-the-art fine-tuning approaches.',
    claims: [
      'In-context few-shot learning emerges at scale (175B parameters).',
      'Removes requirement for task-specific gradient fine-tuning.',
    ],
    methodology: 'Autoregressive Transformer Decoder scaled to 175 Billion parameters.',
    dataset: 'SuperGLUE, LAMBADA',
    metric: '71.8 SuperGLUE F1',
    baseline: 'T5-11B fine-tuned',
    gap: 'High computational inference cost and hallucination.',
    x: 580,
    y: 160,
  },
  {
    id: 'paper-dao2022',
    title: 'FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness',
    authors: ['Tri Dao', 'Daniel Y. Fu', 'Stefano Ermon', 'Atri Rudra', 'Christopher Ré'],
    year: 2022,
    venue: 'NeurIPS 2022',
    citations: 5400,
    cluster: 'Optimization',
    abstract:
      'Transformers are slow and memory-hungry on long sequences. We propose FlashAttention, an IO-aware exact attention algorithm that uses tiling to reduce the number of memory reads/writes between GPU HBM and SRAM.',
    claims: [
      '2-4x wall-clock speedup on exact attention without approximation.',
      'Enables training on 8x longer sequence lengths on standard GPUs.',
    ],
    methodology: 'Tiling attention computations to fit in fast SRAM and fused GPU kernel.',
    dataset: 'Path-X 128k, Long Range Arena',
    metric: '3.5x Speedup',
    baseline: 'Standard PyTorch Attention',
    gap: 'Requires custom CUDA/Triton hardware-level implementation.',
    x: 520,
    y: 420,
  },
  {
    id: 'paper-touvron2023',
    title: 'LLaMA: Open and Efficient Foundation Language Models',
    authors: ['Hugo Touvron', 'Thibaut Lavril', 'Gautier Izacard', 'Xavier Martinet'],
    year: 2023,
    venue: 'arXiv 2023',
    citations: 18000,
    cluster: 'Data & Evaluation',
    abstract:
      'We introduce LLaMA, a collection of foundation language models ranging from 7B to 65B parameters. We train our models on trillions of tokens using publicly available datasets exclusively.',
    claims: [
      'LLaMA-13B outperforms GPT-3 (175B) on most benchmarks.',
      'Demonstrates importance of training token volume over parameter size.',
    ],
    methodology: 'Chinchilla-optimal token overtraining with SwiGLU activations and RoPE embeddings.',
    dataset: 'MMLU, GSM8K, HumanEval',
    metric: '68.9% MMLU',
    baseline: 'GPT-3, OPT-66B',
    gap: 'Base models lack instruction alignment out-of-the-box.',
    x: 260,
    y: 400,
  },
];

const INITIAL_EDGES: CitationEdge[] = [
  { id: 'e1', source: 'paper-devlin2018', target: 'paper-vaswani2017', type: 'extends' },
  { id: 'e2', source: 'paper-brown2020', target: 'paper-vaswani2017', type: 'extends' },
  { id: 'e3', source: 'paper-dao2022', target: 'paper-vaswani2017', type: 'cites' },
  { id: 'e4', source: 'paper-touvron2023', target: 'paper-vaswani2017', type: 'cites' },
  { id: 'e5', source: 'paper-touvron2023', target: 'paper-brown2020', type: 'compares_against' },
  { id: 'e6', source: 'paper-dao2022', target: 'paper-brown2020', type: 'cites' },
];

const CLUSTER_COLORS: Record<PaperNode['cluster'], string> = {
  Architecture: '#1288ff',
  Optimization: '#10b981',
  'Theoretical Analysis': '#8b5cf6',
  'Data & Evaluation': '#f59e0b',
};

export function CitationGraph() {
  const [papers] = useState<PaperNode[]>(INITIAL_PAPERS);
  const [edges] = useState<CitationEdge[]>(INITIAL_EDGES);
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(INITIAL_PAPERS[0].id);
  const [activeTab, setActiveTab] = useState<'graph' | 'matrix'>('graph');
  const [searchFilter, setSearchFilter] = useState('');
  const [selectedCluster, setSelectedCluster] = useState<string>('all');
  const [zoom, setZoom] = useState(1);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const selectedPaper = useMemo(
    () => papers.find((p) => p.id === selectedPaperId) || null,
    [papers, selectedPaperId]
  );

  const filteredPapers = useMemo(() => {
    return papers.filter((p) => {
      const matchCluster = selectedCluster === 'all' || p.cluster === selectedCluster;
      const q = searchFilter.toLowerCase().trim();
      const matchSearch =
        !q ||
        p.title.toLowerCase().includes(q) ||
        p.authors.some((a) => a.toLowerCase().includes(q)) ||
        p.methodology.toLowerCase().includes(q);
      return matchCluster && matchSearch;
    });
  }, [papers, selectedCluster, searchFilter]);

  const activeEdgeIds = useMemo(() => {
    if (!selectedPaperId) return new Set<string>();
    const matched = edges.filter(
      (e) => e.source === selectedPaperId || e.target === selectedPaperId
    );
    return new Set(matched.map((e) => e.id));
  }, [edges, selectedPaperId]);

  const handleZoom = useCallback((delta: number) => {
    setZoom((prev) => Math.min(Math.max(prev + delta, 0.5), 2));
  }, []);

  return (
    <div className="flex flex-col flex-1 h-full overflow-hidden bg-bg">
      {/* Top Toolbar */}
      <header className="flex items-center justify-between px-4 sm:px-6 h-13 bg-surface border-b border-border shrink-0 gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Network size={18} className="text-primary" />
            <h2 className="text-sm font-semibold text-text">Research Citation Graph</h2>
          </div>

          {/* View Mode Switcher */}
          <div className="flex items-center gap-1 bg-bg border border-border rounded-lg p-0.5 ml-2">
            <button
              type="button"
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                activeTab === 'graph' ? 'bg-surface text-primary shadow-xs' : 'text-text-dim hover:text-text'
              }`}
              onClick={() => setActiveTab('graph')}
            >
              <Network size={13} />
              <span>Graph View</span>
            </button>
            <button
              type="button"
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                activeTab === 'matrix' ? 'bg-surface text-primary shadow-xs' : 'text-text-dim hover:text-text'
              }`}
              onClick={() => setActiveTab('matrix')}
            >
              <TableIcon size={13} />
              <span>Literature Matrix</span>
            </button>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-2">
          <div className="relative hidden md:block w-48">
            <Search size={13} className="absolute left-2.5 top-2 text-text-dim" />
            <input
              type="text"
              className="w-full bg-bg border border-border rounded-lg pl-7 pr-2.5 py-1 text-xs text-text placeholder-text-dim focus:outline-none focus:border-primary"
              placeholder="Search graph..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
            />
          </div>

          <select
            className="bg-bg border border-border text-xs rounded-lg px-2 py-1 text-text-dim focus:outline-none focus:border-primary"
            value={selectedCluster}
            onChange={(e) => setSelectedCluster(e.target.value)}
          >
            <option value="all">All Clusters</option>
            <option value="Architecture">Architecture</option>
            <option value="Optimization">Optimization</option>
            <option value="Theoretical Analysis">Theory</option>
            <option value="Data & Evaluation">Data & Eval</option>
          </select>
        </div>
      </header>

      {/* Main Graph Content */}
      <div className="flex flex-1 overflow-hidden relative">
        {activeTab === 'matrix' ? (
          <LiteratureMatrix
            papers={papers}
            selectedPaperId={selectedPaperId || undefined}
            onSelectPaper={(p) => setSelectedPaperId(p.id)}
          />
        ) : (
          <div className="flex-1 flex flex-col relative bg-bg overflow-hidden">
            {/* Zoom Floating Controls */}
            <div className="absolute left-4 bottom-4 z-10 flex items-center gap-1 bg-surface/90 backdrop-blur border border-border rounded-lg p-1 shadow-md">
              <button
                type="button"
                className="p-1.5 text-text-dim hover:text-text rounded transition-colors"
                onClick={() => handleZoom(0.15)}
                title="Zoom In"
              >
                <ZoomIn size={15} />
              </button>
              <button
                type="button"
                className="p-1.5 text-text-dim hover:text-text rounded transition-colors"
                onClick={() => handleZoom(-0.15)}
                title="Zoom Out"
              >
                <ZoomOut size={15} />
              </button>
              <button
                type="button"
                className="p-1.5 text-text-dim hover:text-text rounded transition-colors"
                onClick={() => setZoom(1)}
                title="Reset Zoom"
              >
                <RotateCcw size={15} />
              </button>
            </div>

            {/* Interactive SVG Canvas */}
            <svg
              ref={svgRef}
              className="w-full h-full cursor-grab active:cursor-grabbing select-none"
              viewBox="0 0 800 600"
            >
              <defs>
                <pattern id="graph-grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#22272e" strokeWidth="0.5" />
                </pattern>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="20"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#444d56" />
                </marker>
                <marker
                  id="arrow-active"
                  viewBox="0 0 10 10"
                  refX="20"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#1288ff" />
                </marker>
              </defs>

              <rect width="100%" height="100%" fill="url(#graph-grid)" />

              <g transform={`scale(${zoom})`} className="origin-center transition-transform duration-150">
                {/* Edges */}
                {edges.map((edge) => {
                  const src = papers.find((p) => p.id === edge.source);
                  const tgt = papers.find((p) => p.id === edge.target);
                  if (!src || !tgt) return null;
                  const isActive = activeEdgeIds.has(edge.id);

                  return (
                    <line
                      key={edge.id}
                      x1={src.x || 0}
                      y1={src.y || 0}
                      x2={tgt.x || 0}
                      y2={tgt.y || 0}
                      stroke={isActive ? '#1288ff' : '#30363d'}
                      strokeWidth={isActive ? 2.5 : 1.5}
                      strokeDasharray={edge.type === 'compares_against' ? '4 3' : undefined}
                      markerEnd={isActive ? 'url(#arrow-active)' : 'url(#arrow)'}
                      className="transition-colors"
                    />
                  );
                })}

                {/* Nodes */}
                {filteredPapers.map((paper) => {
                  const isSelected = paper.id === selectedPaperId;
                  const clusterColor = CLUSTER_COLORS[paper.cluster] || '#1288ff';
                  const radius = Math.min(Math.max(18 + Math.log10(paper.citations + 1) * 3, 16), 34);

                  return (
                    <g
                      key={paper.id}
                      transform={`translate(${paper.x || 0}, ${paper.y || 0})`}
                      className="cursor-pointer group"
                      onClick={() => setSelectedPaperId(paper.id)}
                    >
                      {isSelected && (
                        <circle
                          r={radius + 8}
                          fill="none"
                          stroke={clusterColor}
                          strokeWidth="2"
                          strokeDasharray="4 2"
                          className="animate-spin origin-center opacity-70"
                        />
                      )}
                      <circle
                        r={radius}
                        fill="#0d1117"
                        stroke={isSelected ? '#ffffff' : clusterColor}
                        strokeWidth={isSelected ? 3 : 2}
                        className="transition-all group-hover:stroke-white shadow-lg"
                      />
                      <text
                        textAnchor="middle"
                        dy=".3em"
                        fill="#ffffff"
                        fontSize="11"
                        fontWeight="bold"
                        className="pointer-events-none font-mono"
                      >
                        {paper.year}
                      </text>
                      <text
                        textAnchor="middle"
                        y={radius + 14}
                        fill={isSelected ? '#ffffff' : '#8b949e'}
                        fontSize="11"
                        fontWeight={isSelected ? '600' : '400'}
                        className="pointer-events-none select-none max-w-xs"
                      >
                        {paper.title.length > 24 ? `${paper.title.slice(0, 24)}...` : paper.title}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>
        )}

        {/* Selected Paper Details Drawer */}
        <aside className="w-84 sm:w-96 shrink-0 h-full border-l border-border bg-surface flex flex-col">
          <PaperCard
            paper={selectedPaper}
            onClose={() => setSelectedPaperId(null)}
            onAddToStudio={() => {
              /* Can emit custom event or link to Paper Studio */
            }}
          />
        </aside>
      </div>
    </div>
  );
}

import React, { useEffect, useMemo, useRef, useState } from 'react';
import cloud from 'd3-cloud';

export interface WordCloudWord {
  text: string;
  value: number;
}

interface WordCloudProps {
  words: WordCloudWord[];
  width?: number;
  height?: number;
  className?: string;
}

interface LayoutWord {
  text: string;
  size: number;
  x?: number;
  y?: number;
  rotate?: number;
  font?: string;
  style?: string;
  weight?: string;
}

const FONT_FAMILY = 'Inter, system-ui, sans-serif';
const COLORS = ['#22d3ee', '#f59e0b', '#34d399', '#a78bfa', '#f472b6', '#60a5fa', '#fb923c'];

const WordCloud: React.FC<WordCloudProps> = ({ words, width = 600, height = 400, className }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: width, h: height });
  const [layoutWords, setLayoutWords] = useState<LayoutWord[]>([]);

  useEffect(() => {
    const cb = () => {
      if (containerRef.current) {
        setDims({
          w: containerRef.current.clientWidth,
          h: containerRef.current.clientHeight || 400,
        });
      }
    };
    cb();
    window.addEventListener('resize', cb);
    return () => window.removeEventListener('resize', cb);
  }, []);

  useEffect(() => {
    if (!words.length) {
      setLayoutWords([]);
      return;
    }

    const maxVal = Math.max(...words.map((w) => w.value), 1);
    const minVal = Math.min(...words.map((w) => w.value), 1);
    const fontSize = (v: number) => 12 + ((v - minVal) / (maxVal - minVal || 1)) * 36;

    const layout = cloud<LayoutWord>()
      .size([dims.w, dims.h])
      .words(words.map((w) => ({ text: w.text, size: fontSize(w.value) })))
      .padding(2)
      .rotate(() => 0)
      .font(FONT_FAMILY)
      .fontSize((d) => d.size!)
      .spiral('archimedean')
      .on('end', (result: LayoutWord[]) => setLayoutWords(result));

    layout.start();
  }, [words, dims]);

  const svgWords = useMemo(() => {
    return layoutWords.map((w, i) => {
      const color = COLORS[i % COLORS.length];
      return (
        <text
          key={`${w.text}-${i}`}
          x={w.x}
          y={w.y}
          fontSize={w.size}
          fontFamily={FONT_FAMILY}
          fontWeight={600}
          fill={color}
          textAnchor="middle"
          dominantBaseline="central"
          style={{ cursor: 'default', opacity: 0.9 }}
        >
          {w.text}
        </text>
      );
    });
  }, [layoutWords]);

  return (
    <div ref={containerRef} className={className} style={{ width: '100%', height: '100%', minHeight: 300 }}>
      <svg width={dims.w} height={dims.h} viewBox={`0 0 ${dims.w} ${dims.h}`}>
        <g transform={`translate(${dims.w / 2}, ${dims.h / 2})`}>
          {svgWords}
        </g>
      </svg>
    </div>
  );
};

export default React.memo(WordCloud);

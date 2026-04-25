import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '../api';

interface Props {
  reportId: string;
  title: string;
  cachedContent?: string;
  onClose: () => void;
}

export function ReportDrawer({ reportId, title, cachedContent, onClose }: Props) {
  const [content, setContent] = useState(cachedContent || '');
  const [loading, setLoading] = useState(!cachedContent);

  useEffect(() => {
    if (cachedContent) return;
    setLoading(true);
    api.getReport(reportId)
      .then((data) => setContent(data.content || 'No content.'))
      .catch(() => setContent('Failed to load report.'))
      .finally(() => setLoading(false));
  }, [reportId, cachedContent]);

  return (
    <div className="report-overlay" onClick={onClose}>
      <div className="report-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="report-header">
          <h3>{title}</h3>
          <button className="report-close" onClick={onClose}>&times;</button>
        </div>
        <div className="report-body">
          {loading ? (
            <div className="report-loading">Loading...</div>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  );
}

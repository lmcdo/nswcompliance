import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { XCircle } from 'lucide-react';
import { AuthorityColors } from '@/lib/design-tokens';

interface NotApplicableCardProps {
  title: string;
  reason: string;
  color?: 'blue' | 'purple' | 'teal';
}

export function NotApplicableCard({ title, reason, color = 'blue' }: NotApplicableCardProps) {
  const colorClasses = {
    blue: {
      border: 'border-blue-200',
      bg: 'bg-blue-50/30',
      title: 'text-blue-900',
      badge: 'bg-gray-100 text-gray-600',
      text: 'text-gray-600'
    },
    purple: {
      border: 'border-purple-200',
      bg: 'bg-purple-50/30',
      title: 'text-purple-900',
      badge: 'bg-gray-100 text-gray-600',
      text: 'text-gray-600'
    },
    teal: {
      border: 'border-teal-200',
      bg: 'bg-teal-50/30',
      title: 'text-teal-900',
      badge: 'bg-gray-100 text-gray-600',
      text: 'text-gray-600'
    }
  };

  const colors = colorClasses[color];

  return (
    <Card className={`${colors.border} ${colors.bg}`}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <CardTitle className={`text-lg ${colors.title}`}>
            {title}
          </CardTitle>
          <XCircle className="h-5 w-5 text-gray-400 flex-shrink-0 mt-0.5" />
        </div>
        <Badge className={colors.badge}>
          Not applicable to this address
        </Badge>
      </CardHeader>
      <CardContent>
        <p className={`text-sm ${colors.text}`}>
          {reason}
        </p>
      </CardContent>
    </Card>
  );
}

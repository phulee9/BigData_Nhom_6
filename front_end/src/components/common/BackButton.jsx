import { ArrowLeft } from 'lucide-react';
import { styles } from '../../styles/styles';

export function BackButton({ onClick, label = 'Quay lại' }) {
  return (
    <button onClick={onClick} style={styles.backButton}>
      <ArrowLeft size={18} style={{ marginRight: '6px' }} />
      {label}
    </button>
  );
}

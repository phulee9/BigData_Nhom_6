import { styles } from '../../styles/styles';

export function Header({ title, subtitle, showLogo = false }) {
  return (
    <div style={styles.header}>
      {showLogo && (
        <div style={styles.logoSection}>
          <div style={styles.logoIcon}>📋</div>
          <h1 style={styles.title}>{title}</h1>
        </div>
      )}
      {!showLogo && <h1 style={styles.title}>{title}</h1>}
      <p style={styles.subtitle}>{subtitle}</p>
    </div>
  );
}

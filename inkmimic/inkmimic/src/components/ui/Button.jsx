export function Button({ variant = 'gold', as: As = 'button', className = '', ...props }) {
  const base = variant === 'gold' ? 'btn-gold' : 'btn-outline';
  return <As className={`${base} ${className}`} {...props} />;
}

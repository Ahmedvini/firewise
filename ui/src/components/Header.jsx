// Page title and short description.
export default function Header({ title, description, eyebrow }) {
  return (
    <header className="page-header">
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h2>{title}</h2>
      {description && <p className="lede">{description}</p>}
    </header>
  );
}

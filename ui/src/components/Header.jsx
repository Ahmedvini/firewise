// Page title, short description and optional "sample data" badge.
export default function Header({ title, description, sample = true }) {
  return (
    <header className="page-header">
      <h2>
        {title} {sample && <span className="tag amber">Sample data</span>}
      </h2>
      {description && <p className="lede">{description}</p>}
    </header>
  );
}

import { Link } from "react-router-dom";

export default function Brand() {
  return (
    <Link className="brand" to="/" aria-label="Vertebra Research home">
      <span className="brand-mark" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </span>
      <span>
        vertebra<span className="brand-sub">RESEARCH</span>
      </span>
    </Link>
  );
}

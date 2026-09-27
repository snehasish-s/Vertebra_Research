import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowDown,
  ArrowRight,
  Check,
  FileText,
  Layers3,
  Quote,
  Search,
} from "lucide-react";
import Brand from "../components/Brand";
import Spine from "../components/Spine";

const stages = [
  [
    "Upload",
    "Start with what you know.",
    "Bring your papers, reports, and notes together. Your PDFs become one searchable research library.",
  ],
  [
    "Text extraction",
    "Make every page readable.",
    "Text is extracted page by page, keeping a connection to where each idea first appeared.",
  ],
  [
    "Chunking",
    "Give ideas room to connect.",
    "Pages become smaller, overlapping passages. Each one remembers its document, page, and place.",
  ],
  [
    "Embeddings",
    "Search beyond exact words.",
    "A model turns each passage into a numerical representation of meaning, ready for comparison.",
  ],
  [
    "Retrieval",
    "Find the evidence that matters.",
    "Your question retrieves the most relevant passages from across your library.",
  ],
  [
    "Grounded answer",
    "Let your sources do the talking.",
    "Only retrieved passages reach the answer model. When the evidence is missing, it should say so.",
  ],
  [
    "Citations",
    "Follow every answer home.",
    "Open a citation to read its source excerpt and the exact PDF page. Research you can check.",
  ],
];

export default function Landing() {
  const [active, setActive] = useState(0);
  const section = useRef(null);
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries)
          if (entry.isIntersecting)
            setActive(Number(entry.target.dataset.stage));
      },
      { rootMargin: "-25% 0px -35% 0px", threshold: 0 },
    );
    section.current
      .querySelectorAll("[data-stage]")
      .forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <header className="site-header">
        <Brand />
        <nav aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <Link className="button small" to="/research">
            Open workspace <ArrowRight size={15} />
          </Link>
        </nav>
      </header>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="status-dot" /> YOUR IDEAS. CONNECTED.
            </div>
            <h1>
              A backbone
              <br />
              for your
              <br />
              <em>research.</em>
            </h1>
            <p>
              Turn a stack of documents into a conversation.
              <br className="desktop-break" /> Find the connections. Follow the
              evidence.
            </p>
            <Link className="button primary" to="/research">
              Start your research <ArrowRight size={18} />
            </Link>
            <div className="hero-details">
              <span>
                <Check size={13} /> Answers with sources
              </span>
              <span>
                <Check size={13} /> Built around your PDFs
              </span>
            </div>
          </div>
          <div className="hero-art">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="art-cross cross-one">+</div>
            <div className="art-cross cross-two">+</div>
            <div className="specimen-label">
              FIG. 01 <span>THE CONNECTED LIBRARY</span>
            </div>
            <Spine active={3} />
            <div className="annotation annotation-one">
              <span className="annotation-line" />
              <FileText size={15} />
              <span>
                Your documents
                <br />
                <b>The starting point</b>
              </span>
            </div>
            <div className="annotation annotation-two">
              <span className="annotation-line" />
              <Search size={15} />
              <span>
                Connected ideas
                <br />
                <b>The bigger picture</b>
              </span>
            </div>
            <div className="annotation annotation-three">
              <span className="annotation-line" />
              <Quote size={15} />
              <span>
                Grounded answers
                <br />
                <b>Evidence you can trace</b>
              </span>
            </div>
            <span className="art-caption">
              A little structure. A lot of possibility.
            </span>
          </div>
          <a className="scroll-hint" href="#how-it-works">
            <ArrowDown size={15} /> SCROLL TO SEE THE CONNECTIONS
          </a>
        </section>
        <div className="principles">
          <span>
            <Layers3 size={19} /> One connected library
          </span>
          <span>
            <Search size={19} /> Questions, not keywords
          </span>
          <span>
            <Quote size={19} /> A source for every answer
          </span>
        </div>
        <section className="process-section" id="how-it-works" ref={section}>
          <div className="process-heading">
            <div className="eyebrow">FROM DOCUMENT TO DISCOVERY</div>
            <h2>
              Good answers have
              <br />
              <em>a strong foundation.</em>
            </h2>
            <p>Seven connected steps. One traceable answer.</p>
          </div>
          <div className="process-grid">
            <div className="process-visual">
              <Spine active={active} compact />
              <span className="process-counter">
                0{active + 1} / 07 <span>{stages[active][0]}</span>
              </span>
              <small>Educational illustration, not a medical model.</small>
            </div>
            <div className="stage-list">
              {stages.map(([name, heading, description], index) => (
                <article
                  key={name}
                  data-stage={index}
                  className={`stage ${active === index ? "active" : ""}`}
                >
                  <div className="stage-label">
                    <span>0{index + 1}</span> {name}
                  </div>
                  <h3>{heading}</h3>
                  <p>{description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
        <section className="closing">
          <div className="eyebrow">LESS SEARCHING. MORE UNDERSTANDING.</div>
          <h2>
            Your next insight
            <br />
            is already in there.
          </h2>
          <Link className="button primary" to="/research">
            Find it in your workspace <ArrowRight size={18} />
          </Link>
        </section>
      </main>
      <footer>
        <Brand />
        <span>Evidence, connected.</span>
        <span>Built for curious minds.</span>
      </footer>
    </>
  );
}

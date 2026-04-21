import type { ReactNode } from "react";

export function Card({
  title,
  description,
  children,
  className = "",
  footer,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
  footer?: ReactNode;
}) {
  return (
    <section className={`glass-card${className ? ` ${className}` : ""}`}>
      <header className="glass-card__header">
        <div>
          <h3 className="glass-card__title">{title}</h3>
          {description ? (
            <p className="glass-card__description">{description}</p>
          ) : null}
        </div>
      </header>
      <div className="glass-card__body">{children}</div>
      {footer ? <div className="glass-card__footer">{footer}</div> : null}
    </section>
  );
}

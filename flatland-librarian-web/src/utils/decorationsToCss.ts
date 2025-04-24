import { CSSProperties } from "react";
import { DecorationType } from "ansi-sequence-parser";


export type SubjectiveHandler = (decoration: DecorationType) => Partial<CSSProperties>;

export default function decorationsToCSS(
  decorations: Set<DecorationType>,
  handleSubjective?: SubjectiveHandler
): CSSProperties {
  const styles: CSSProperties = {};

  for (const deco of decorations) {
    switch (deco) {
      case "bold":
        styles.fontWeight = "bold";
        break;
      case "italic":
        styles.fontStyle = "italic";
        break;
      case "underline":
      case "overline":
      case "strikethrough": {
        const existing = styles.textDecoration ? styles.textDecoration + " " : "";
        const value =
          deco === "strikethrough" ? "line-through" : deco;
        styles.textDecoration = existing + value;
        break;
      }
      default:
        if (handleSubjective) {
          Object.assign(styles, handleSubjective(deco));
        }
    }
  }

  return styles;
}
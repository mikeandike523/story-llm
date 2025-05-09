import { css, keyframes } from "@emotion/react";
import { forwardRef } from "react";
import { Div, DivProps } from "style-props-html";

const spinnerAnimation = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
`;

export interface LoadingSpinnerProps extends DivProps {
  size: string | number;
  thickness: string | number;
  fadeSeconds: number;
  show: boolean;
  spinnerPrimaryColor: string;
  spinnerSecondaryColor?: string;
  spinnerBackgroundColor?: string;
  spinnerProps?: Partial<DivProps>;
  periodSeconds: number;
}

export default forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  function LoadingSpinner(
    {
      periodSeconds = 1,
      fadeSeconds,
      show,
      size,
      thickness,
      spinnerPrimaryColor,
      spinnerSecondaryColor="transparent",
      spinnerBackgroundColor="transparent",
      spinnerProps={},
      ...rest
    },
    ref
  ) {
    const sizeString = typeof size === "number"? `${size}px` : size;
    const thicknessString = typeof thickness === "number"? `${thickness}px` : thickness;
    return (
      <Div
        ref={ref}
        display="flex"
        pointerEvents={show ? "auto" : "none"}
        opacity={show ? 1 : 0}
        transition={`opacity ${fadeSeconds}s ease-in-out`}
        alignItems="center"
        justifyContent="center"
        {...rest}
      >
        <Div
          width={sizeString}
          height={sizeString}
          css={css`
            background-color: ${spinnerBackgroundColor};
            border-radius: 50%;
            border: ${thicknessString} solid ${spinnerPrimaryColor};
            border-top: ${thicknessString} solid ${spinnerSecondaryColor};
            animation: ${spinnerAnimation} ${periodSeconds}s linear infinite;
          `}
          {...spinnerProps}
        ></Div>
      </Div>
    );
  }
);

import { RefObject, useEffect, useState } from "react";
import _ from "lodash";

export default function useMeasureElement<TElem extends HTMLElement, TMeas>(
    ref: RefObject<TElem | null>,
    measure: (element: TElem)=> TMeas
  ): TMeas | null {
    const [measurement, setMeasurement] = useState<TMeas | null>(null);
  
    useEffect(() => {
      if (!ref.current) return;
  
      // Function to update the rect state
      const updateRect = () => {
        if (ref.current) {
          setMeasurement(measure(ref.current));
        }
      };
  
      // Initial measurement
      updateRect();
  
      // Throttled update function
      const throttledUpdateRect = _.throttle(updateRect, 100, { trailing: true });
  
      // Try to use ResizeObserver if available
      let resizeObserver: ResizeObserver | null = null;
  
      if (typeof ResizeObserver !== "undefined") {
        resizeObserver = new ResizeObserver(throttledUpdateRect);
        resizeObserver.observe(ref.current);
      } else {
        // Fallback to window resize event
        window.addEventListener("resize", throttledUpdateRect);
      }
  
      const current = ref.current;
  
      // Cleanup function
      return () => {
        throttledUpdateRect.cancel();
  
        if (resizeObserver) {
          if (current) {
            resizeObserver.unobserve(current);
          }
          resizeObserver.disconnect();
        } else {
          window.removeEventListener("resize", throttledUpdateRect);
        }
      };
    }, [measure, ref]);
  
    return measurement;
  }
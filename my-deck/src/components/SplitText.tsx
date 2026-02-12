import React, { useRef } from 'react';
import { gsap } from 'gsap';
import { useGSAP } from '@gsap/react';

interface SplitTextProps {
  text: string;
  className?: string;
  delay?: number;
  duration?: number;
}

const SplitText: React.FC<SplitTextProps> = ({
  text,
  className = '',
  delay = 0,
  duration = 0.5
}) => {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    const chars = ref.current?.querySelectorAll('.split-char');
    if (chars) {
      gsap.fromTo(chars,
        {
          opacity: 0,
          y: 40,
          scale: 1.2,
          filter: 'blur(10px)'
        },
        {
          opacity: 1,
          y: 0,
          scale: 1,
          filter: 'blur(0px)',
          duration: duration,
          stagger: 0.05,
          delay: delay / 1000,
          ease: 'back.out(1.2)'
        }
      );
    }
  }, { scope: ref, dependencies: [text, delay, duration] });

  return (
    <div ref={ref} className={`${className} inline-block overflow-hidden`}>
      {text.split('').map((char, i) => (
        <span
          key={i}
          className="split-char inline-block"
          style={{ whiteSpace: 'pre' }}
        >
          {char}
        </span>
      ))}
    </div>
  );
};

export default SplitText;

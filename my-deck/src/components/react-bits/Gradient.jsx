import { motion } from 'framer-motion';

const Gradient = ({ className = "" }) => {
    return (
        <div className={`absolute inset-0 -z-10 overflow-hidden ${className}`}>
            <motion.div
                animate={{
                    scale: [1, 1.2, 1],
                    rotate: [0, 15, -15, 0],
                }}
                transition={{
                    duration: 20,
                    repeat: Infinity,
                    ease: "linear"
                }}
                className="absolute -top-[50%] -left-[50%] w-[200%] h-[200%] bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-indigo-900/40 via-slate-900/60 to-slate-900"
            />
        </div>
    );
};

export default Gradient;

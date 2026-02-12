import { motion } from 'framer-motion';

const SplitText = ({ text, className = "", delay = 0 }) => {
    // Placeholder for SplitText animation
    // In a real React Bits implementation, this would split text into characters/words
    // and animate them individually.
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: delay, ease: "easeOut" }}
            className={className}
        >
            {text}
        </motion.div>
    );
};

export default SplitText;

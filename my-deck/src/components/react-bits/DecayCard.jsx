import { motion } from 'framer-motion';

const DecayCard = ({ children, className = "" }) => {
    return (
        <motion.div
            whileHover={{ scale: 1.02, rotate: 1 }}
            className={`border border-white/10 bg-white/5 backdrop-blur-sm rounded-xl p-6 ${className}`}
        >
            {children}
        </motion.div>
    );
};

export default DecayCard;

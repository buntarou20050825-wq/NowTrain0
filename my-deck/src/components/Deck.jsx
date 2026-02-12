import React from 'react';
import { Deck, Slide, Box, Text, FlexBox } from 'spectacle';

// Placeholder slides imports (will be implemented later)
import Slide1_Intro from '../slides/Slide1_Intro';
import Slide2_Problem from '../slides/Slide2_Problem';
import Slide3_Architecture from '../slides/Slide3_Architecture';
import Slide4_Realtime from '../slides/Slide4_Realtime';
import Slide5_Frontend from '../slides/Slide5_Frontend';
import Slide6_Backend from '../slides/Slide6_Backend';
import Slide7_Challenges from '../slides/Slide7_Challenges';
import Slide8_Future from '../slides/Slide8_Future';
import Slide9_End from '../slides/Slide9_End';

const theme = {
    colors: {
        primary: '#e0e0e0', // Light gray text
        secondary: '#818cf8', // Indigo accent
        tertiary: '#0f172a', // Dark background (Slate 900)
        quaternary: '#fca5a5', // Red accent
    },
    fonts: {
        header: '"Inter", sans-serif',
        text: '"Inter", sans-serif',
    },
};

const template = () => (
    <FlexBox
        justifyContent="space-between"
        position="absolute"
        bottom={0}
        width={1}
        padding="0 2em"
    >
        <Box padding="0 1em">
            <Text fontSize="12px" color="primary">NowTrain Presentation</Text>
        </Box>
        <Box padding="0 1em">
            <Text fontSize="12px" color="primary">@bunta</Text>
        </Box>
    </FlexBox>
);

export default function Presentation() {
    return (
        <Deck theme={theme} template={template}>
            <Slide1_Intro />
            <Slide2_Problem />
            <Slide3_Architecture />
            <Slide4_Realtime />
            <Slide5_Frontend />
            <Slide6_Backend />
            <Slide7_Challenges />
            <Slide8_Future />
            <Slide9_End />
        </Deck>
    );
}

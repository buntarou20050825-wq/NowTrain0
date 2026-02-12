import React from 'react';
import { Slide, FlexBox, Heading, Text } from 'spectacle';
import SplitText from '../components/react-bits/SplitText';
import Gradient from '../components/react-bits/Gradient';

const Slide1_Intro = () => {
    return (
        <Slide>
            <Gradient />
            <FlexBox height="100%" flexDirection="column" justifyContent="center" alignItems="center">
                <SplitText
                    text="NowTrain"
                    className="text-8xl font-black text-white mb-4 tracking-tighter"
                    delay={0.2}
                />
                <Heading fontSize="h3" color="secondary">
                    リアルタイム公共交通可視化システム
                </Heading>
                <Text color="primary" fontSize="24px" className="mt-8">
                    「いつ来るか」を「どこにいるか」へ
                </Text>
            </FlexBox>
        </Slide>
    );
};

export default Slide1_Intro;

import React from 'react';
import { Slide, FlexBox, Heading, Text, Link } from 'spectacle';
import SplitText from '../components/react-bits/SplitText';

const Slide9_End = () => {
    return (
        <Slide backgroundColor="tertiary">
            <FlexBox height="100%" flexDirection="column" alignItems="center" justifyContent="center">
                <SplitText
                    text="Thank You!"
                    className="text-9xl font-black text-white mb-8 tracking-tighter"
                    delay={0}
                />

                <Heading fontSize="h4" color="secondary" className="mt-8">
                    ご清聴ありがとうございました
                </Heading>

                <FlexBox flexDirection="column" className="mt-16 bg-white/5 p-8 rounded-xl">
                    <Text color="primary" fontSize="24px">
                        GitHub Repository
                    </Text>
                    <Link href="https://github.com/buntarou20050825-wq/NowTrain" target="_blank">
                        <Text color="quaternary" fontSize="20px" className="underline cursor-pointer">
                            github.com/buntarou20050825-wq/NowTrain
                        </Text>
                    </Link>
                </FlexBox>
            </FlexBox>
        </Slide>
    );
};

export default Slide9_End;

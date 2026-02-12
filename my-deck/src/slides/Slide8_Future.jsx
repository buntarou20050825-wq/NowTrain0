import React from 'react';
import { Slide, FlexBox, Heading, Text } from 'spectacle';
import Gradient from '../components/react-bits/Gradient';

const Slide8_Future = () => {
    return (
        <Slide backgroundColor="tertiary">
            <Gradient className="opacity-50" />
            <FlexBox height="100%" flexDirection="column" alignItems="center">
                <Heading fontSize="h3" color="secondary">
                    今後の展望
                </Heading>

                <FlexBox flexDirection="column" alignItems="flex-start" className="w-[80%] mt-12 bg-white/5 p-8 rounded-2xl backdrop-blur-md border border-white/10">
                    <Text color="primary" fontSize="32px" className="mb-4">
                        🚀 E2Eテストの完全自動化
                    </Text>
                    <Text color="gray-400" fontSize="24px" className="ml-8 mb-8">
                        Playwrightを用いたシナリオテストの拡充
                    </Text>

                    <Text color="primary" fontSize="32px" className="mb-4">
                        🔮 混雑予測AIの統合
                    </Text>
                    <Text color="gray-400" fontSize="24px" className="ml-8 mb-8">
                        過去データから「座れる車両」を推論
                    </Text>

                    <Text color="primary" fontSize="32px" className="mb-4">
                        📱 Native App化 (React Native)
                    </Text>
                    <Text color="gray-400" fontSize="24px" className="ml-8">
                        プッシュ通知で「そろそろ家を出て！」とお知らせ
                    </Text>
                </FlexBox>
            </FlexBox>
        </Slide>
    );
};

export default Slide8_Future;

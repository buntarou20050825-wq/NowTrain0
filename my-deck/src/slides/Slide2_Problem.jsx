import React from 'react';
import { Slide, FlexBox, Heading, Text, Grid, Box } from 'spectacle';
import DecayCard from '../components/react-bits/DecayCard';

const Slide2_Problem = () => {
    return (
        <Slide backgroundColor="tertiary">
            <FlexBox height="100%" flexDirection="column" alignItems="center" justifyContent="center">
                <Heading fontSize="h2" color="secondary" margin="0px 0px 50px 0px">
                    背景と課題
                </Heading>
                <Grid gridTemplateColumns="1fr 1fr" gridGap={50} width="80%">
                    <DecayCard className="h-full flex flex-col justify-center items-center text-center">
                        <Heading fontSize="h4" color="quaternary">
                            従来の課題
                        </Heading>
                        <Text color="primary">
                            「あと何分？」はわかるけど...<br />
                            遅延時に<br />
                            <strong>「電車が今どこにいるか」</strong><br />
                            わからない不安
                        </Text>
                    </DecayCard>

                    <DecayCard className="h-full flex flex-col justify-center items-center text-center">
                        <Heading fontSize="h4" color="secondary">
                            NowTrainの解決策
                        </Heading>
                        <Text color="primary">
                            地図上で<br />
                            <strong>リアルタイム位置</strong>を可視化。<br />
                            自分の乗る列車を<br />
                            「見て」安心する体験。
                        </Text>
                    </DecayCard>
                </Grid>
            </FlexBox>
        </Slide>
    );
};

export default Slide2_Problem;
